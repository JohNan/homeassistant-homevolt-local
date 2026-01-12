"""Sensor platform for Homevolt Local integration."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_AGGREGATED,
    ATTR_EMS,
    ATTR_ERROR_STR,
    ATTR_PHASE,
    ATTR_SENSORS,
    BMS_DATA_INDEX_TOTAL,
    DOMAIN,
    SENSOR_TYPE_GRID,
    SENSOR_TYPE_LOAD,
    SENSOR_TYPE_SOLAR,
)
from .coordinator import HomevoltDataUpdateCoordinator
from .models import HomevoltData

_LOGGER = logging.getLogger(__name__)


def _safe_float(value: Any) -> float | None:
    """Safely convert a value to float or return None."""
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_energy_val(value: Any) -> float | None:
    """Return absolute energy value (or None if invalid).

    For sensor data that is already in kWh (floats from the API).
    """
    v = _safe_float(value)
    if v is None:
        return None
    return abs(v)


def _raw_energy_val(value: Any) -> float | None:
    """Return raw (signed) energy value or None.

    For sensor data that is already in kWh (floats from the API).
    """
    return _safe_float(value)


def _rssi_icon(value: Any) -> str:
    """Return an mdi wifi-strength icon name for an RSSI value in dBm.

    Higher (less negative) values map to stronger icons. None/invalid -> off.
    """
    try:
        if value is None:
            return "mdi:wifi-strength-off"
        v = float(value)
    except (TypeError, ValueError):
        return "mdi:wifi-strength-off"

    if v >= -55:
        return "mdi:wifi-strength-4"
    if v >= -70:
        return "mdi:wifi-strength-3"
    if v >= -85:
        return "mdi:wifi-strength-2"
    return "mdi:wifi-strength-1"


def _rssi_icon_for_sensor(data: HomevoltData, sensor_type: str) -> str:
    """Get RSSI value for a sensor type and return appropriate icon."""
    val = next((s.rssi for s in data.sensors if s.type == sensor_type), None)
    return _rssi_icon(val)


def _battery_icon(soc_value: Any, charging: bool = False) -> str:
    """Return appropriate mdi battery icon for SOC and charging state.

    `soc_value` expected 0..100. If None/invalid -> unknown icon.
    """
    try:
        if soc_value is None:
            return "mdi:battery-unknown"
        soc = float(soc_value)
    except (TypeError, ValueError):
        return "mdi:battery-unknown"

    if soc >= 95:
        return "mdi:battery-charging-100" if charging else "mdi:battery"
    if soc >= 80:
        return "mdi:battery-charging-80" if charging else "mdi:battery-90"
    if soc >= 60:
        return "mdi:battery-charging-60" if charging else "mdi:battery-80"
    if soc >= 40:
        return "mdi:battery-charging-40" if charging else "mdi:battery-60"
    if soc >= 20:
        return "mdi:battery-charging-20" if charging else "mdi:battery-40"
    return "mdi:battery-charging-10" if charging else "mdi:battery-10"


def _ems_is_charging(data: HomevoltData, ems_index: int) -> bool:
    """Return True if given EMS device appears to be charging.

    Use `op_state_str` when available, fallback to `ems_data.power < 0` heuristic.
    """
    try:
        ems = data.ems[ems_index]
    except (IndexError, TypeError, AttributeError):
        return False

    # Prefer explicit op_state string
    try:
        op = ems.op_state_str
        if op and isinstance(op, str):
            low = op.lower()
            if "charge" in low or "charging" in low:
                return True
            if "discharge" in low or "discharging" in low:
                return False
    except (AttributeError, TypeError) as exc:
        _LOGGER.debug("Error checking op_state_str for ems %s: %s", ems_index, exc)

    # No reliable fallback available; assume not charging to avoid false positives.
    return False


def _battery_icon_for_ems(data: HomevoltData, ems_index: int) -> str:
    """Return battery icon for EMS `soc_avg` and charging state."""
    try:
        soc = None
        if data.ems and len(data.ems) > ems_index:
            raw = data.ems[ems_index].ems_data.soc_avg
            soc = float(raw) / 100 if raw is not None else None
        charging = _ems_is_charging(data, ems_index)
        return _battery_icon(soc, charging)
    except (IndexError, TypeError, AttributeError, ValueError):
        return "mdi:battery-unknown"


def _battery_icon_for_bms(data: HomevoltData, ems_index: int, bms_index: int) -> str:
    """Return battery icon for a specific BMS cell/module SOC."""
    try:
        soc = None
        if data.ems and len(data.ems) > ems_index:
            ems = data.ems[ems_index]
            if ems.bms_data and len(ems.bms_data) > bms_index:
                raw = ems.bms_data[bms_index].soc
                soc = float(raw) / 100 if raw is not None else None
        charging = _ems_is_charging(data, ems_index)
        return _battery_icon(soc, charging)
    except (IndexError, TypeError, AttributeError, ValueError):
        return "mdi:battery-unknown"


def _battery_icon_for_aggregated(data: HomevoltData) -> str:
    """Return battery icon for aggregated total SOC."""
    try:
        soc = None
        if (
            data.aggregated
            and data.aggregated.bms_data
            and len(data.aggregated.bms_data) > BMS_DATA_INDEX_TOTAL
        ):
            raw = data.aggregated.bms_data[BMS_DATA_INDEX_TOTAL].soc
            soc = float(raw) / 100 if raw is not None else None
        charging = False
        try:
            op = data.aggregated.op_state_str
            if op and isinstance(op, str):
                low = op.lower()
                if "charge" in low or "charging" in low:
                    charging = True
        except (AttributeError, TypeError) as exc:
            _LOGGER.debug("Error checking aggregated op_state_str: %s", exc)
        return _battery_icon(soc, charging)
    except (IndexError, TypeError, AttributeError, ValueError):
        return "mdi:battery-unknown"


def get_current_schedule(data: HomevoltData) -> str:
    """Get the current active schedule."""
    now = datetime.now()
    for schedule in data.schedules:
        try:
            if schedule.from_time is None or schedule.to_time is None:
                continue
            from_time = datetime.fromisoformat(schedule.from_time)
            to_time = datetime.fromisoformat(schedule.to_time)
            if from_time <= now < to_time:
                return schedule.type if schedule.type else "Unknown"
        except (ValueError, TypeError):
            continue
    return "No active schedule"


@dataclass(frozen=True, kw_only=True)
class HomevoltSensorEntityDescription(SensorEntityDescription):
    """Describes Homevolt sensor entity."""

    value_fn: Callable[[HomevoltData], Any] | None = None
    icon_fn: Callable[[HomevoltData], str] | None = None
    raw_value_fn: Callable[[HomevoltData], Any] | None = None
    attrs_fn: Callable[[HomevoltData], dict[str, Any]] | None = None
    device_specific: bool = (
        False  # Whether this sensor is specific to a device in the ems array
    )
    sensor_specific: bool = (
        False  # Whether this sensor is specific to a device in the sensors array
    )
    sensor_type: str | None = None  # Type of sensor: grid, solar, load


SENSOR_DESCRIPTIONS: tuple[HomevoltSensorEntityDescription, ...] = (
    # Aggregated device sensors
    HomevoltSensorEntityDescription(
        key="ems",
        translation_key="status",
        icon="mdi:state-machine",
        value_fn=lambda data: data.aggregated.ems_data.state_str,
        attrs_fn=lambda data: {
            ATTR_EMS: [ems.__dict__ for ems in data.ems] if data.ems else [],
            ATTR_AGGREGATED: data.aggregated.__dict__ if data.aggregated else {},
            ATTR_SENSORS: [sensor.__dict__ for sensor in data.sensors]
            if data.sensors
            else [],
        },
    ),
    HomevoltSensorEntityDescription(
        key="current_schedule",
        translation_key="current_schedule",
        icon="mdi:calendar-clock",
        value_fn=get_current_schedule,
        attrs_fn=lambda data: {
            "schedules": [schedule.__dict__ for schedule in data.schedules],
            "schedule_count": data.schedule_count,
            "schedule_current_id": data.schedule_current_id,
        },
    ),
    HomevoltSensorEntityDescription(
        key="ems_error",
        translation_key="error",
        icon="mdi:battery-unknown",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.aggregated.error_str[:255]
        if data.aggregated.error_str
        else None,
        attrs_fn=lambda data: {
            ATTR_ERROR_STR: data.aggregated.error_str,
        },
    ),
    HomevoltSensorEntityDescription(
        key="total_soc",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        icon_fn=_battery_icon_for_aggregated,
        value_fn=lambda data: float(data.aggregated.bms_data[BMS_DATA_INDEX_TOTAL].soc)
        / 100
        if data.aggregated.bms_data
        and len(data.aggregated.bms_data) > BMS_DATA_INDEX_TOTAL
        else None,
    ),
    HomevoltSensorEntityDescription(
        key="power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        icon="mdi:battery-sync-outline",
        value_fn=lambda data: data.aggregated.ems_data.power,
    ),
    HomevoltSensorEntityDescription(
        key="energy_discharged",
        translation_key="energy_discharged",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:battery-positive",
        value_fn=lambda data: _normalize_energy_val(
            data.aggregated.ems_aggregate.exported_kwh
        ),
        raw_value_fn=lambda data: _raw_energy_val(
            data.aggregated.ems_aggregate.exported_kwh
        ),
    ),
    HomevoltSensorEntityDescription(
        key="energy_charged",
        translation_key="energy_charged",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:battery-negative",
        value_fn=lambda data: _normalize_energy_val(
            data.aggregated.ems_aggregate.imported_kwh
        ),
        raw_value_fn=lambda data: _raw_energy_val(
            data.aggregated.ems_aggregate.imported_kwh
        ),
    ),
    HomevoltSensorEntityDescription(
        key="rated_capacity",
        translation_key="rated_capacity",
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        icon="mdi:battery-plus",
        value_fn=lambda data: data.aggregated.ems_info.rated_capacity,
    ),
    HomevoltSensorEntityDescription(
        key="charge_status",
        translation_key="charge_status",
        icon="mdi:battery-sync",
        value_fn=lambda data: data.aggregated.op_state_str,
    ),
    # Sensor-specific sensors for grid, solar, and load
    # Grid sensors
    HomevoltSensorEntityDescription(
        key="grid_power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        icon="mdi:transmission-tower",
        value_fn=lambda data: next(
            (s.total_power for s in data.sensors if s.type == SENSOR_TYPE_GRID), None
        ),
        attrs_fn=lambda data: {
            ATTR_PHASE: next(
                (s.phase for s in data.sensors if s.type == SENSOR_TYPE_GRID), None
            ),
        },
        sensor_specific=True,
        sensor_type=SENSOR_TYPE_GRID,
    ),
    HomevoltSensorEntityDescription(
        key="grid_energy_imported",
        translation_key="energy_imported",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:transmission-tower-import",
        value_fn=lambda data: _normalize_energy_val(
            next(
                (s.energy_imported for s in data.sensors if s.type == SENSOR_TYPE_GRID),
                None,
            )
        ),
        raw_value_fn=lambda data: _raw_energy_val(
            next(
                (s.energy_imported for s in data.sensors if s.type == SENSOR_TYPE_GRID),
                None,
            )
        ),
        sensor_specific=True,
        sensor_type=SENSOR_TYPE_GRID,
    ),
    HomevoltSensorEntityDescription(
        key="grid_energy_exported",
        translation_key="energy_exported",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:transmission-tower-export",
        value_fn=lambda data: _normalize_energy_val(
            next(
                (s.energy_exported for s in data.sensors if s.type == SENSOR_TYPE_GRID),
                None,
            )
        ),
        raw_value_fn=lambda data: _raw_energy_val(
            next(
                (s.energy_exported for s in data.sensors if s.type == SENSOR_TYPE_GRID),
                None,
            )
        ),
        sensor_specific=True,
        sensor_type=SENSOR_TYPE_GRID,
    ),
    HomevoltSensorEntityDescription(
        key="grid_rssi",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        icon_fn=lambda data: _rssi_icon_for_sensor(data, SENSOR_TYPE_GRID),
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: next(
            (s.rssi for s in data.sensors if s.type == SENSOR_TYPE_GRID),
            None,
        ),
        sensor_specific=True,
        sensor_type=SENSOR_TYPE_GRID,
    ),
    HomevoltSensorEntityDescription(
        key="grid_pdr",
        translation_key="packet_delivery_rate",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:signal-variant",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: next(
            (s.pdr for s in data.sensors if s.type == SENSOR_TYPE_GRID),
            None,
        ),
        sensor_specific=True,
        sensor_type=SENSOR_TYPE_GRID,
    ),
    # Solar sensors
    HomevoltSensorEntityDescription(
        key="solar_power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        icon="mdi:solar-power",
        value_fn=lambda data: next(
            (s.total_power for s in data.sensors if s.type == SENSOR_TYPE_SOLAR), None
        ),
        attrs_fn=lambda data: {
            ATTR_PHASE: next(
                (s.phase for s in data.sensors if s.type == SENSOR_TYPE_SOLAR), None
            ),
        },
        sensor_specific=True,
        sensor_type=SENSOR_TYPE_SOLAR,
    ),
    HomevoltSensorEntityDescription(
        key="solar_energy_imported",
        translation_key="energy_imported",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:solar-power-variant",
        value_fn=lambda data: _normalize_energy_val(
            next(
                (
                    s.energy_imported
                    for s in data.sensors
                    if s.type == SENSOR_TYPE_SOLAR
                ),
                None,
            )
        ),
        raw_value_fn=lambda data: _raw_energy_val(
            next(
                (
                    s.energy_imported
                    for s in data.sensors
                    if s.type == SENSOR_TYPE_SOLAR
                ),
                None,
            )
        ),
        sensor_specific=True,
        sensor_type=SENSOR_TYPE_SOLAR,
    ),
    HomevoltSensorEntityDescription(
        key="solar_energy_exported",
        translation_key="energy_exported",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:solar-power-variant-outline",
        value_fn=lambda data: _normalize_energy_val(
            next(
                (
                    s.energy_exported
                    for s in data.sensors
                    if s.type == SENSOR_TYPE_SOLAR
                ),
                None,
            )
        ),
        raw_value_fn=lambda data: _raw_energy_val(
            next(
                (
                    s.energy_exported
                    for s in data.sensors
                    if s.type == SENSOR_TYPE_SOLAR
                ),
                None,
            )
        ),
        sensor_specific=True,
        sensor_type=SENSOR_TYPE_SOLAR,
    ),
    HomevoltSensorEntityDescription(
        key="solar_rssi",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        icon_fn=lambda data: _rssi_icon_for_sensor(data, SENSOR_TYPE_SOLAR),
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: next(
            (s.rssi for s in data.sensors if s.type == SENSOR_TYPE_SOLAR),
            None,
        ),
        sensor_specific=True,
        sensor_type=SENSOR_TYPE_SOLAR,
    ),
    HomevoltSensorEntityDescription(
        key="solar_pdr",
        translation_key="packet_delivery_rate",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:signal-variant",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: next(
            (s.pdr for s in data.sensors if s.type == SENSOR_TYPE_SOLAR),
            None,
        ),
        sensor_specific=True,
        sensor_type=SENSOR_TYPE_SOLAR,
    ),
    # Load sensors
    HomevoltSensorEntityDescription(
        key="load_power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        icon="mdi:home-lightning-bolt",
        value_fn=lambda data: next(
            (s.total_power for s in data.sensors if s.type == SENSOR_TYPE_LOAD), None
        ),
        attrs_fn=lambda data: {
            ATTR_PHASE: next(
                (s.phase for s in data.sensors if s.type == SENSOR_TYPE_LOAD), None
            ),
        },
        sensor_specific=True,
        sensor_type=SENSOR_TYPE_LOAD,
    ),
    HomevoltSensorEntityDescription(
        key="load_energy_imported",
        translation_key="energy_imported",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:home-import-outline",
        value_fn=lambda data: _normalize_energy_val(
            next(
                (s.energy_imported for s in data.sensors if s.type == SENSOR_TYPE_LOAD),
                None,
            )
        ),
        raw_value_fn=lambda data: _raw_energy_val(
            next(
                (s.energy_imported for s in data.sensors if s.type == SENSOR_TYPE_LOAD),
                None,
            )
        ),
        sensor_specific=True,
        sensor_type=SENSOR_TYPE_LOAD,
    ),
    HomevoltSensorEntityDescription(
        key="load_energy_exported",
        translation_key="energy_exported",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:home-export-outline",
        value_fn=lambda data: _normalize_energy_val(
            next(
                (s.energy_exported for s in data.sensors if s.type == SENSOR_TYPE_LOAD),
                None,
            )
        ),
        raw_value_fn=lambda data: _raw_energy_val(
            next(
                (s.energy_exported for s in data.sensors if s.type == SENSOR_TYPE_LOAD),
                None,
            )
        ),
        sensor_specific=True,
        sensor_type=SENSOR_TYPE_LOAD,
    ),
)


class HomevoltSensor(CoordinatorEntity[HomevoltDataUpdateCoordinator], SensorEntity):
    """Representation of a Homevolt sensor."""

    _attr_has_entity_name = True
    entity_description: HomevoltSensorEntityDescription

    def __init__(
        self,
        coordinator: HomevoltDataUpdateCoordinator,
        description: HomevoltSensorEntityDescription,
        ems_index: int | None = None,
        sensor_index: int | None = None,
        bms_index: int | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self.ems_index = ems_index
        self.sensor_index = sensor_index
        self.bms_index = bms_index
        self._extra_attributes: dict[str, Any] = {}

        # Create a unique ID based on the device properties if available
        if (
            bms_index is not None
            and ems_index is not None
            and coordinator.data
            and coordinator.data.ems
        ):
            # BMS (Battery) sensor - use ems ecu_id + bms serial for unique ID
            try:
                ems_device = coordinator.data.ems[ems_index]
                ecu_id = ems_device.ecu_id or f"unknown_{ems_index}"
                bms_info = (
                    ems_device.bms_info[bms_index] if ems_device.bms_info else None
                )
                bms_serial = (
                    bms_info.serial_number
                    if bms_info and bms_info.serial_number
                    else f"bms_{bms_index}"
                )
                self._attr_unique_id = (
                    f"{DOMAIN}_{description.key}_bms_{ecu_id}_{bms_serial}"
                )
            except IndexError:
                self._attr_unique_id = (
                    f"{DOMAIN}_{description.key}_bms_{ems_index}_{bms_index}"
                )
        elif ems_index is not None and coordinator.data and coordinator.data.ems:
            try:
                # Use the ecu_id for a consistent unique ID
                # across different IP addresses
                ems_device = coordinator.data.ems[ems_index]
                ecu_id = ems_device.ecu_id or f"unknown_{ems_index}"
                self._attr_unique_id = f"{DOMAIN}_{description.key}_ems_{ecu_id}"
            except IndexError:
                # Fallback to a generic unique ID if we can't get the ecu_id
                self._attr_unique_id = f"{DOMAIN}_{description.key}_ems_{ems_index}"
        elif sensor_index is not None and coordinator.data and coordinator.data.sensors:
            try:
                # Use the euid for a consistent unique ID across different IP addresses
                sensor_data = coordinator.data.sensors[sensor_index]
                euid = sensor_data.euid
                # Check for null/default euid (all zeros = virtual sensor)
                # For these, use main device ID + sensor type for uniqueness
                if not euid or euid == "0000000000000000":
                    main_id = self.coordinator.get_main_device_id()
                    sensor_type = sensor_data.type
                    if not sensor_type:
                        # This is unexpected - virtual sensors should have a type
                        # Log warning so users know about potential data issues
                        _LOGGER.warning(
                            "Sensor at index %s has null EUID but no type. "
                            "This may cause entity migration issues. "
                            "Using fallback unique ID.",
                            sensor_index,
                        )
                        sensor_type = f"sensor_{sensor_index}"
                    self._attr_unique_id = (
                        f"{DOMAIN}_{description.key}_{main_id}_{sensor_type}"
                    )
                else:
                    self._attr_unique_id = f"{DOMAIN}_{description.key}_sensor_{euid}"
            except IndexError:
                # Fallback to a generic unique ID if we can't get the euid
                self._attr_unique_id = (
                    f"{DOMAIN}_{description.key}_sensor_{sensor_index}"
                )
        else:
            # For aggregated sensors, use the first ecu_id for a stable unique ID
            # that doesn't change when IP changes
            main_id = self.coordinator.get_main_device_id()
            self._attr_unique_id = f"{DOMAIN}_{description.key}_{main_id}"

        self._attr_device_info = self.device_info

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this Homevolt device."""
        # Main aggregated device ID - use ecu_id for consistency across IP changes
        main_device_id = f"homevolt_{self.coordinator.get_main_device_id()}"

        # BMS (Battery) device - sub-device of the Inverter
        if (
            self.bms_index is not None
            and self.ems_index is not None
            and self.coordinator.data
            and self.coordinator.data.ems
        ):
            try:
                ems_device = self.coordinator.data.ems[self.ems_index]
                ecu_id = ems_device.ecu_id or f"unknown_{self.ems_index}"
                inverter_device_id = f"ems_{ecu_id}"

                # Get BMS info for this battery
                bms_info = (
                    ems_device.bms_info[self.bms_index]
                    if ems_device.bms_info and len(ems_device.bms_info) > self.bms_index
                    else None
                )
                bms_serial = (
                    bms_info.serial_number
                    if bms_info and bms_info.serial_number
                    else f"bms_{self.bms_index}"
                )
                bms_fw = bms_info.fw_version if bms_info else ""
                bms_id = bms_info.id + 1 if bms_info else self.bms_index + 1
                inverter_num = self.ems_index + 1

                return DeviceInfo(
                    identifiers={(DOMAIN, f"bms_{ecu_id}_{bms_serial}")},
                    translation_key="battery",
                    translation_placeholders={
                        "inverter_num": str(inverter_num),
                        "battery_num": str(bms_id),
                    },
                    manufacturer="Homevolt",
                    model="Battery Module",
                    entry_type=DeviceEntryType.SERVICE,
                    via_device=(DOMAIN, inverter_device_id),  # Link to Inverter
                    sw_version=bms_fw,
                    hw_version=bms_serial,
                )
            except IndexError:
                return DeviceInfo(
                    identifiers={
                        (DOMAIN, f"bms_unknown_{self.ems_index}_{self.bms_index}")
                    },
                    translation_key="battery",
                    translation_placeholders={
                        "inverter_num": str(self.ems_index + 1),
                        "battery_num": str(self.bms_index + 1),
                    },
                    manufacturer="Homevolt",
                    model="Battery Module",
                    entry_type=DeviceEntryType.SERVICE,
                    via_device=(DOMAIN, main_device_id),
                )
        elif (
            self.ems_index is not None
            and self.coordinator.data
            and self.coordinator.data.ems
        ):
            # Get device-specific information from the ems data
            try:
                ems_device = self.coordinator.data.ems[self.ems_index]
                ecu_id = ems_device.ecu_id or f"unknown_{self.ems_index}"
                serial_number = (
                    ems_device.inv_info.serial_number if ems_device.inv_info else ""
                )

                # Try to get more detailed information for the device name
                fw_version = (
                    ems_device.ems_info.fw_version if ems_device.ems_info else ""
                )

                # Use the ecu_id as the unique identifier, which should be consistent
                # across different IP addresses for the same physical device
                return DeviceInfo(
                    identifiers={(DOMAIN, f"ems_{ecu_id}")},
                    translation_key="inverter",
                    translation_placeholders={"inverter_num": str(self.ems_index + 1)},
                    manufacturer="Homevolt",
                    model=f"Energy Management System {fw_version}",
                    entry_type=DeviceEntryType.SERVICE,
                    via_device=(DOMAIN, main_device_id),  # Link to the main device
                    sw_version=fw_version,
                    hw_version=serial_number,
                )
            except IndexError:
                # Fallback to a generic device info if we can't get specific info
                return DeviceInfo(
                    identifiers={(DOMAIN, f"ems_unknown_{self.ems_index}")},
                    translation_key="inverter",
                    translation_placeholders={"inverter_num": str(self.ems_index + 1)},
                    manufacturer="Homevolt",
                    model="Energy Management System",
                    entry_type=DeviceEntryType.SERVICE,
                    via_device=(DOMAIN, main_device_id),  # Link to the main device
                )
        elif (
            self.sensor_index is not None
            and self.coordinator.data
            and self.coordinator.data.sensors
        ):
            # Get device-specific information from the sensors data
            try:
                sensor_data = self.coordinator.data.sensors[self.sensor_index]
                sensor_type = sensor_data.type or "unknown"
                node_id = sensor_data.node_id
                euid = sensor_data.euid or "unknown"

                # Capitalize the first letter of the sensor type for the name
                sensor_type_name = sensor_type.capitalize()

                # Map sensor type to translation key
                translation_key_map = {
                    "grid": "grid",
                    "solar": "solar",
                    "load": "load",
                }
                device_translation_key = translation_key_map.get(sensor_type.lower())

                # Use the euid as the unique identifier, which should be consistent
                # across different IP addresses for the same physical sensor
                if device_translation_key:
                    return DeviceInfo(
                        identifiers={(DOMAIN, f"sensor_{euid}")},
                        translation_key=device_translation_key,
                        manufacturer="Homevolt",
                        model=f"{sensor_type_name} Sensor (Node {node_id})",
                        entry_type=DeviceEntryType.SERVICE,
                        via_device=(DOMAIN, main_device_id),  # Link to the main device
                    )
                else:
                    return DeviceInfo(
                        identifiers={(DOMAIN, f"sensor_{euid}")},
                        name=sensor_type_name,
                        manufacturer="Homevolt",
                        model=f"{sensor_type_name} Sensor (Node {node_id})",
                        entry_type=DeviceEntryType.SERVICE,
                        via_device=(DOMAIN, main_device_id),  # Link to the main device
                    )
            except IndexError:
                # Fallback to a generic device info if we can't get specific info
                return DeviceInfo(
                    identifiers={(DOMAIN, f"sensor_unknown_{self.sensor_index}")},
                    name=f"Sensor {self.sensor_index + 1}",
                    manufacturer="Homevolt",
                    model="Sensor",
                    entry_type=DeviceEntryType.SERVICE,
                    via_device=(DOMAIN, main_device_id),  # Link to the main device
                )
        else:
            # For aggregated sensors or if no ems_index or sensor_index is provided
            return DeviceInfo(
                identifiers={(DOMAIN, main_device_id)},
                translation_key="system",
                manufacturer="Homevolt",
                model="Energy Management System",
                entry_type=DeviceEntryType.SERVICE,
            )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return self._extra_attributes

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.coordinator.data is None:
            self._attr_native_value = None
            self._extra_attributes = {}
            self.async_write_ha_state()
            return

        try:
            data = self.coordinator.data

            # Check if this is a device-specific sensor and if the device exists
            if self.ems_index is not None and data.ems:
                # Verify the device index is valid
                if len(data.ems) <= self.ems_index:
                    _LOGGER.error(
                        "Device index %s is out of range for %s "
                        "(only %s devices available)",
                        self.ems_index,
                        self.entity_description.name,
                        len(data.ems),
                    )
                    self._attr_native_value = None
                    self._extra_attributes = {}
                    self.async_write_ha_state()
                    return

            # Check if this is a sensor-specific sensor and if the sensor exists
            elif self.sensor_index is not None and data.sensors:
                # Verify the sensor index is valid
                if len(data.sensors) <= self.sensor_index:
                    _LOGGER.error(
                        "Sensor index %s is out of range for %s "
                        "(only %s sensors available)",
                        self.sensor_index,
                        self.entity_description.name,
                        len(data.sensors),
                    )
                    self._attr_native_value = None
                    self._extra_attributes = {}
                    self.async_write_ha_state()
                    return

                # Verify the sensor type matches the expected type
                if self.entity_description.sensor_type:
                    sensor_type = data.sensors[self.sensor_index].type
                    if sensor_type != self.entity_description.sensor_type:
                        # Try to find a sensor with the expected type
                        found = False
                        for idx, sensor in enumerate(data.sensors):
                            if sensor.type == self.entity_description.sensor_type:
                                self.sensor_index = idx
                                found = True
                                break

                        if not found:
                            _LOGGER.error(
                                "Sensor type %s not found for %s",
                                self.entity_description.sensor_type,
                                self.entity_description.name,
                            )
                            self._attr_native_value = None
                            self._extra_attributes = {}
                            self.async_write_ha_state()
                            return

            # Set value using the value_fn from the description
            if self.entity_description.value_fn:
                if self.ems_index is not None:
                    # For device-specific sensors, pass the device index to the value_fn
                    self._attr_native_value = self.entity_description.value_fn(data)
                elif self.sensor_index is not None:
                    # For sensor-specific sensors, pass the sensor index to the value_fn
                    self._attr_native_value = self.entity_description.value_fn(data)
                else:
                    # For aggregated sensors, just pass the data
                    self._attr_native_value = self.entity_description.value_fn(data)

            # Set icon using the icon_fn from the description if available
            if self.entity_description.icon_fn:
                if self.ems_index is not None:
                    # For device-specific sensors, pass the device index to the icon_fn
                    self._attr_icon = self.entity_description.icon_fn(data)
                elif self.sensor_index is not None:
                    # For sensor-specific sensors, pass the sensor index to the icon_fn
                    self._attr_icon = self.entity_description.icon_fn(data)
                else:
                    # For aggregated sensors, just pass the data
                    self._attr_icon = self.entity_description.icon_fn(data)

            # Set attributes using the attrs_fn from the description if available
            if self.entity_description.attrs_fn:
                if self.ems_index is not None:
                    # For device-specific sensors, pass the device index to the attrs_fn
                    self._extra_attributes = self.entity_description.attrs_fn(data)
                elif self.sensor_index is not None:
                    # For sensor-specific sensors, pass the sensor index to the attrs_fn
                    self._extra_attributes = self.entity_description.attrs_fn(data)
                else:
                    # For aggregated sensors, just pass the data
                    self._extra_attributes = self.entity_description.attrs_fn(data)

            # Preserve raw signed energy value if a raw_value_fn is provided
            if self.entity_description.raw_value_fn:
                try:
                    raw_val = self.entity_description.raw_value_fn(data)
                    if raw_val is not None:
                        if not isinstance(self._extra_attributes, dict):
                            self._extra_attributes = {}
                        self._extra_attributes["raw_energy"] = raw_val
                except (
                    KeyError,
                    TypeError,
                    IndexError,
                    ValueError,
                    AttributeError,
                ) as err:
                    _LOGGER.debug(
                        "Could not extract raw energy for %s: %s",
                        self.entity_description.name,
                        err,
                    )

        except (KeyError, TypeError, IndexError, ValueError, AttributeError) as err:
            _LOGGER.error(
                "Error extracting sensor data for %s: %s",
                self.entity_description.name,
                err,
            )
            self._attr_native_value = None
            self._extra_attributes = {}

        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Homevolt Local sensor based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    sensors = []

    # Create non-device-specific sensors (aggregated data)
    for description in SENSOR_DESCRIPTIONS:
        if not description.device_specific and not description.sensor_specific:
            sensors.append(HomevoltSensor(coordinator, description))

    # Check if we have data and if the ems array exists
    if coordinator.data and coordinator.data.ems:
        # Create device-specific sensors for each device in the ems array
        for idx, ems_device in enumerate(coordinator.data.ems):
            # Add a status sensor for each device
            sensors.append(
                HomevoltSensor(
                    coordinator,
                    HomevoltSensorEntityDescription(
                        key=f"ems_{idx + 1}_status",
                        translation_key="status",
                        icon="mdi:information-outline",
                        value_fn=lambda data, i=idx: data.ems[i].ems_data.state_str,
                        device_specific=True,
                    ),
                    ems_index=idx,
                )
            )
            # Add a temperature sensor for each device
            sensors.append(
                HomevoltSensor(
                    coordinator,
                    HomevoltSensorEntityDescription(
                        key=f"ems_{idx + 1}_temp",
                        device_class=SensorDeviceClass.TEMPERATURE,
                        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
                        state_class=SensorStateClass.MEASUREMENT,
                        value_fn=lambda data, i=idx: float(
                            data.ems[i].ems_data.sys_temp
                        )
                        / 10,
                        icon="mdi:thermometer",
                        device_specific=True,
                    ),
                    ems_index=idx,
                )
            )
            # Add a SoC sensor for each device
            sensors.append(
                HomevoltSensor(
                    coordinator,
                    HomevoltSensorEntityDescription(
                        key=f"ems_{idx + 1}_soc",
                        device_class=SensorDeviceClass.BATTERY,
                        native_unit_of_measurement=PERCENTAGE,
                        state_class=SensorStateClass.MEASUREMENT,
                        icon_fn=lambda data, i=idx: _battery_icon_for_ems(data, i),
                        value_fn=lambda data, i=idx: float(data.ems[i].ems_data.soc_avg)
                        / 100,
                        device_specific=True,
                    ),
                    ems_index=idx,
                )
            )
            # Add a power sensor for each device
            sensors.append(
                HomevoltSensor(
                    coordinator,
                    HomevoltSensorEntityDescription(
                        key=f"ems_{idx + 1}_power",
                        device_class=SensorDeviceClass.POWER,
                        state_class=SensorStateClass.MEASUREMENT,
                        native_unit_of_measurement=UnitOfPower.WATT,
                        icon="mdi:battery-sync-outline",
                        value_fn=lambda data, i=idx: data.ems[i].ems_data.power,
                        device_specific=True,
                    ),
                    ems_index=idx,
                )
            )
            # Add an energy discharged sensor for each device
            sensors.append(
                HomevoltSensor(
                    coordinator,
                    HomevoltSensorEntityDescription(
                        key=f"ems_{idx + 1}_energy_discharged",
                        translation_key="energy_discharged",
                        device_class=SensorDeviceClass.ENERGY,
                        state_class=SensorStateClass.TOTAL_INCREASING,
                        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                        icon="mdi:battery-positive",
                        value_fn=lambda data, i=idx: _normalize_energy_val(
                            data.ems[i].ems_aggregate.exported_kwh
                        ),
                        raw_value_fn=lambda data, i=idx: _raw_energy_val(
                            data.ems[i].ems_aggregate.exported_kwh
                        ),
                        device_specific=True,
                    ),
                    ems_index=idx,
                )
            )
            # Add an energy charged sensor for each device
            sensors.append(
                HomevoltSensor(
                    coordinator,
                    HomevoltSensorEntityDescription(
                        key=f"ems_{idx + 1}_energy_charged",
                        translation_key="energy_charged",
                        device_class=SensorDeviceClass.ENERGY,
                        state_class=SensorStateClass.TOTAL_INCREASING,
                        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                        icon="mdi:battery-negative",
                        value_fn=lambda data, i=idx: _normalize_energy_val(
                            data.ems[i].ems_aggregate.imported_kwh
                        ),
                        raw_value_fn=lambda data, i=idx: _raw_energy_val(
                            data.ems[i].ems_aggregate.imported_kwh
                        ),
                        device_specific=True,
                    ),
                    ems_index=idx,
                )
            )
            # Add an error sensor for each device
            sensors.append(
                HomevoltSensor(
                    coordinator,
                    HomevoltSensorEntityDescription(
                        key=f"ems_{idx + 1}_error",
                        translation_key="error",
                        icon="mdi:battery-unknown",
                        value_fn=lambda data, i=idx: data.ems[i].error_str[:255]
                        if data.ems[i].error_str
                        else None,
                        attrs_fn=lambda data, i=idx: {
                            ATTR_ERROR_STR: data.ems[i].error_str,
                        },
                        entity_category=EntityCategory.DIAGNOSTIC,
                        device_specific=True,
                    ),
                    ems_index=idx,
                )
            )
            # Add a rated capacity sensor for each device
            sensors.append(
                HomevoltSensor(
                    coordinator,
                    HomevoltSensorEntityDescription(
                        key=f"ems_{idx + 1}_rated_capacity",
                        translation_key="rated_capacity",
                        device_class=SensorDeviceClass.ENERGY_STORAGE,
                        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
                        icon="mdi:battery-plus",
                        value_fn=lambda data, i=idx: data.ems[
                            i
                        ].ems_info.rated_capacity,
                        device_specific=True,
                    ),
                    ems_index=idx,
                )
            )
            # Add a charge status sensor for each device
            sensors.append(
                HomevoltSensor(
                    coordinator,
                    HomevoltSensorEntityDescription(
                        key=f"ems_{idx + 1}_charge_status",
                        translation_key="charge_status",
                        icon="mdi:battery-sync",
                        value_fn=lambda data, i=idx: data.ems[i].op_state_str,
                        device_specific=True,
                    ),
                    ems_index=idx,
                )
            )

            # Create battery sensors for this ems device
            if ems_device.bms_data:
                for bms_idx, _bms_device in enumerate(ems_device.bms_data):
                    sensors.append(
                        HomevoltSensor(
                            coordinator,
                            HomevoltSensorEntityDescription(
                                key=f"ems_{idx + 1}_bms_{bms_idx + 1}_rated_capacity",
                                translation_key="rated_capacity",
                                device_class=SensorDeviceClass.ENERGY_STORAGE,
                                native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
                                icon="mdi:battery-plus",
                                value_fn=lambda data, i=idx, j=bms_idx: data.ems[i]
                                .bms_info[j]
                                .rated_cap,
                                device_specific=True,
                            ),
                            ems_index=idx,
                            bms_index=bms_idx,
                        )
                    )
                    sensors.append(
                        HomevoltSensor(
                            coordinator,
                            HomevoltSensorEntityDescription(
                                key=f"ems_{idx + 1}_bms_{bms_idx + 1}_soc",
                                device_class=SensorDeviceClass.BATTERY,
                                native_unit_of_measurement=PERCENTAGE,
                                state_class=SensorStateClass.MEASUREMENT,
                                icon_fn=lambda data, i=idx, j=bms_idx: (
                                    _battery_icon_for_bms(data, i, j)
                                ),
                                value_fn=lambda data, i=idx, j=bms_idx: float(
                                    data.ems[i].bms_data[j].soc
                                )
                                / 100,
                                device_specific=True,
                            ),
                            ems_index=idx,
                            bms_index=bms_idx,
                        )
                    )
                    # Add a max temperature sensor for each battery
                    sensors.append(
                        HomevoltSensor(
                            coordinator,
                            HomevoltSensorEntityDescription(
                                key=f"ems_{idx + 1}_bms_{bms_idx + 1}_tmax",
                                translation_key="max_temperature",
                                device_class=SensorDeviceClass.TEMPERATURE,
                                native_unit_of_measurement=UnitOfTemperature.CELSIUS,
                                state_class=SensorStateClass.MEASUREMENT,
                                value_fn=lambda data, i=idx, j=bms_idx: float(
                                    data.ems[i].bms_data[j].tmax
                                )
                                / 10,
                                icon="mdi:thermometer-chevron-up",
                                device_specific=True,
                            ),
                            ems_index=idx,
                            bms_index=bms_idx,
                        )
                    )
                    # Add a min temperature sensor for each battery
                    sensors.append(
                        HomevoltSensor(
                            coordinator,
                            HomevoltSensorEntityDescription(
                                key=f"ems_{idx + 1}_bms_{bms_idx + 1}_tmin",
                                translation_key="min_temperature",
                                device_class=SensorDeviceClass.TEMPERATURE,
                                native_unit_of_measurement=UnitOfTemperature.CELSIUS,
                                state_class=SensorStateClass.MEASUREMENT,
                                value_fn=lambda data, i=idx, j=bms_idx: float(
                                    data.ems[i].bms_data[j].tmin
                                )
                                / 10,
                                icon="mdi:thermometer-chevron-down",
                                device_specific=True,
                            ),
                            ems_index=idx,
                            bms_index=bms_idx,
                        )
                    )

    # Check if we have data and if the sensors array exists
    if coordinator.data and coordinator.data.sensors:
        sensors_data = coordinator.data.sensors

        # Create a set of available sensor types
        available_sensor_types = set()
        for sensor in sensors_data:
            # Skip sensors that are marked as not available
            if sensor.available is False:
                continue

            sensor_type = sensor.type
            if sensor_type:
                available_sensor_types.add(sensor_type)

        # Create sensor-specific sensors for each sensor type
        for description in SENSOR_DESCRIPTIONS:
            if description.sensor_specific and description.sensor_type:
                # Check if we have a sensor of this type
                if description.sensor_type in available_sensor_types:
                    # Find the index of the sensor with this type
                    for idx, sensor in enumerate(sensors_data):
                        if (
                            sensor.type == description.sensor_type
                            and sensor.available is not False
                        ):
                            # Create a sensor for this type
                            sensors.append(
                                HomevoltSensor(coordinator, description, None, idx)
                            )
                            break

    async_add_entities(sensors)
