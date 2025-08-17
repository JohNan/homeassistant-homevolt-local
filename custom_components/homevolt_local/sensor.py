"""Sensor platform for Homevolt Local integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Union

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HomevoltDataUpdateCoordinator
from .const import (
    ATTR_AGGREGATED,
    ATTR_EMS,
    ATTR_ERROR_STR,
    ATTR_PHASE,
    ATTR_SENSORS,
    BMS_DATA_INDEX_DEVICE,
    BMS_DATA_INDEX_TOTAL,
    DOMAIN,
    SENSOR_TYPE_GRID,
    SENSOR_TYPE_LOAD,
    SENSOR_TYPE_SOLAR,
)
from .models import HomevoltData

_LOGGER = logging.getLogger(__name__)


def get_current_schedule(data: HomevoltData) -> str:
    """Get the current active schedule."""
    now = datetime.now(timezone.utc)
    for schedule in data.schedules:
        try:
            from_time = datetime.fromisoformat(schedule.from_time).replace(
                tzinfo=timezone.utc
            )
            to_time = datetime.fromisoformat(schedule.to_time).replace(
                tzinfo=timezone.utc
            )
            if from_time <= now < to_time:
                return schedule.type
        except (ValueError, TypeError):
            continue
    return "No active schedule"


@dataclass(frozen=True, kw_only=True)
class HomevoltSensorEntityDescription(SensorEntityDescription):
    """Describes Homevolt sensor entity."""

    value_fn: Callable[[Union[HomevoltData, Dict[str, Any]]], Any] | None = None
    icon_fn: Callable[[Union[HomevoltData, Dict[str, Any]]], str] | None = None
    attrs_fn: Callable[[Union[HomevoltData, Dict[str, Any]]], Dict[str, Any]] | None = (
        None
    )
    device_specific: bool = False
    sensor_specific: bool = False
    sensor_type: str | None = None


SENSOR_DESCRIPTIONS: tuple[HomevoltSensorEntityDescription, ...] = (
    # Aggregated device sensors
    HomevoltSensorEntityDescription(
        key="ems",
        name="Homevolt Status",
        value_fn=lambda data: data.aggregated.ems_data.state_str,
        icon_fn=lambda data: (
            "mdi:battery-outline"
            if float(data.aggregated.ems_data.soc_avg) < 5
            else f"mdi:battery-{int(round(float(data.aggregated.ems_data.soc_avg) / 10.0) * 10)}"
        ),
        attrs_fn=lambda data: {
            ATTR_EMS: [ems.__dict__ for ems in data.ems] if data.ems else [],
            ATTR_AGGREGATED: data.aggregated.__dict__ if data.aggregated else {},
            ATTR_SENSORS: [
                sensor.__dict__ for sensor in data.sensors
            ]
            if data.sensors
            else [],
        },
    ),
    HomevoltSensorEntityDescription(
        key="current_schedule",
        name="Homevolt Current Schedule",
        icon="mdi:calendar-clock",
        value_fn=get_current_schedule,
        attrs_fn=lambda data: {
            "schedules": [schedule.__dict__ for schedule in data.schedules]
        },
    ),
    HomevoltSensorEntityDescription(
        key="ems_error",
        name="Homevolt Error",
        icon="mdi:battery-unknown",
        value_fn=lambda data: data.aggregated.error_str[:255]
        if data.aggregated.error_str
        else None,
        attrs_fn=lambda data: {
            ATTR_ERROR_STR: data.aggregated.error_str,
        },
    ),
    HomevoltSensorEntityDescription(
        key="battery_soc",
        name="Homevolt battery SoC",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement="%",
        value_fn=lambda data, idx=0: float(
            data.ems[idx].bms_data[BMS_DATA_INDEX_DEVICE].soc
        )
        / 100
        if idx < len(data.ems)
        else None,
        device_specific=True,
    ),
    HomevoltSensorEntityDescription(
        key="total_soc",
        name="Homevolt Total SoC",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement="%",
        value_fn=lambda data: float(
            data.aggregated.bms_data[BMS_DATA_INDEX_TOTAL].soc
        )
        / 100
        if data.aggregated.bms_data
        and len(data.aggregated.bms_data) > BMS_DATA_INDEX_TOTAL
        else None,
    ),
    HomevoltSensorEntityDescription(
        key="power",
        name="Homevolt Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement="W",
        icon="mdi:battery-sync-outline",
        value_fn=lambda data: data.aggregated.ems_data.power,
    ),
    HomevoltSensorEntityDescription(
        key="energy_produced",
        name="Homevolt Energy Produced",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
        icon="mdi:battery-positive",
        value_fn=lambda data: float(data.aggregated.ems_data.energy_produced) / 1000,
    ),
    HomevoltSensorEntityDescription(
        key="energy_consumed",
        name="Homevolt Energy Consumed",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
        icon="mdi:battery-negative",
        value_fn=lambda data: float(data.aggregated.ems_data.energy_consumed) / 1000,
    ),
    # Device-specific sensors for each EMS device
    HomevoltSensorEntityDescription(
        key="device_status",
        name="Status",
        value_fn=lambda data, idx=0: data.ems[idx].ems_data.state_str
        if idx < len(data.ems)
        else None,
        icon_fn=lambda data, idx=0: (
            "mdi:battery-outline"
            if idx < len(data.ems) and float(data.ems[idx].ems_data.soc_avg) < 5
            else f"mdi:battery-{int(round(float(data.ems[idx].ems_data.soc_avg) / 10.0) * 10) if idx < len(data.ems) else 0}"
        ),
        device_specific=True,
    ),
    HomevoltSensorEntityDescription(
        key="device_power",
        name="Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement="W",
        icon="mdi:battery-sync-outline",
        value_fn=lambda data, idx=0: data.ems[idx].ems_data.power
        if idx < len(data.ems)
        else None,
        device_specific=True,
    ),
    HomevoltSensorEntityDescription(
        key="device_energy_produced",
        name="Energy Produced",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
        icon="mdi:battery-positive",
        value_fn=lambda data, idx=0: float(data.ems[idx].ems_data.energy_produced)
        / 1000
        if idx < len(data.ems)
        else None,
        device_specific=True,
    ),
    HomevoltSensorEntityDescription(
        key="device_energy_consumed",
        name="Energy Consumed",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
        icon="mdi:battery-negative",
        value_fn=lambda data, idx=0: float(data.ems[idx].ems_data.energy_consumed)
        / 1000
        if idx < len(data.ems)
        else None,
        device_specific=True,
    ),
    HomevoltSensorEntityDescription(
        key="device_error",
        name="Error",
        icon="mdi:battery-unknown",
        value_fn=lambda data, idx=0: data.ems[idx].error_str[:255]
        """Sensor platform for Homevolt Local integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Union

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HomevoltDataUpdateCoordinator
from .const import (
    ATTR_AGGREGATED,
    ATTR_EMS,
    ATTR_ERROR_STR,
    ATTR_PHASE,
    ATTR_SENSORS,
    BMS_DATA_INDEX_DEVICE,
    BMS_DATA_INDEX_TOTAL,
    DOMAIN,
    SENSOR_TYPE_GRID,
    SENSOR_TYPE_LOAD,
    SENSOR_TYPE_SOLAR,
)
from .models import HomevoltData

_LOGGER = logging.getLogger(__name__)


def get_current_schedule(data: HomevoltData) -> str:
    """Get the current active schedule."""
    now = datetime.now(timezone.utc)
    for schedule in data.schedules:
        try:
            from_time = datetime.fromisoformat(schedule.from_time).replace(
                tzinfo=timezone.utc
            )
            to_time = datetime.fromisoformat(schedule.to_time).replace(
                tzinfo=timezone.utc
            )
            if from_time <= now < to_time:
                return schedule.type
        except (ValueError, TypeError):
            continue
    return "No active schedule"


def _get_battery_icon(soc: float) -> str:
    """Return the battery icon for a given SoC."""
    if soc < 5:
        return "mdi:battery-outline"
    return f"mdi:battery-{int(round(soc / 10.0) * 10)}"


@dataclass(frozen=True, kw_only=True)
class HomevoltSensorEntityDescription(SensorEntityDescription):
    """Describes Homevolt sensor entity."""

    value_fn: Callable[[Union[HomevoltData, Dict[str, Any]]], Any] | None = None
    icon_fn: Callable[[Union[HomevoltData, Dict[str, Any]]], str] | None = None
    attrs_fn: Callable[[Union[HomevoltData, Dict[str, Any]]], Dict[str, Any]] | None = (
        None
    )
    device_specific: bool = False
    sensor_specific: bool = False
    sensor_type: str | None = None


SENSOR_DESCRIPTIONS: tuple[HomevoltSensorEntityDescription, ...] = (
    # Aggregated device sensors
    HomevoltSensorEntityDescription(
        key="ems",
        name="Homevolt Status",
        value_fn=lambda data: data.aggregated.ems_data.state_str,
        icon_fn=lambda data: _get_battery_icon(float(data.aggregated.ems_data.soc_avg)),
        attrs_fn=lambda data: {
            ATTR_EMS: [ems.__dict__ for ems in data.ems] if data.ems else [],
            ATTR_AGGREGATED: data.aggregated.__dict__ if data.aggregated else {},
            ATTR_SENSORS: [
                sensor.__dict__ for sensor in data.sensors
            ]
            if data.sensors
            else [],
        },
    ),
    HomevoltSensorEntityDescription(
        key="current_schedule",
        name="Homevolt Current Schedule",
        icon="mdi:calendar-clock",
        value_fn=get_current_schedule,
        attrs_fn=lambda data: {
            "schedules": [schedule.__dict__ for schedule in data.schedules]
        },
    ),
    HomevoltSensorEntityDescription(
        key="ems_error",
        name="Homevolt Error",
        icon="mdi:battery-unknown",
        value_fn=lambda data: data.aggregated.error_str[:255]
        if data.aggregated.error_str
        else None,
        attrs_fn=lambda data: {
            ATTR_ERROR_STR: data.aggregated.error_str,
        },
    ),
    HomevoltSensorEntityDescription(
        key="battery_soc",
        name="Homevolt battery SoC",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement="%",
        value_fn=lambda data, idx=0: float(
            data.ems[idx].bms_data[BMS_DATA_INDEX_DEVICE].soc
        )
        / 100
        if idx < len(data.ems)
        else None,
        device_specific=True,
    ),
    HomevoltSensorEntityDescription(
        key="total_soc",
        name="Homevolt Total SoC",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement="%",
        value_fn=lambda data: float(
            data.aggregated.bms_data[BMS_DATA_INDEX_TOTAL].soc
        )
        / 100
        if data.aggregated.bms_data
        and len(data.aggregated.bms_data) > BMS_DATA_INDEX_TOTAL
        else None,
    ),
    HomevoltSensorEntityDescription(
        key="power",
        name="Homevolt Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement="W",
        icon="mdi:battery-sync-outline",
        value_fn=lambda data: data.aggregated.ems_data.power,
    ),
    HomevoltSensorEntityDescription(
        key="energy_produced",
        name="Homevolt Energy Produced",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
        icon="mdi:battery-positive",
        value_fn=lambda data: float(data.aggregated.ems_data.energy_produced) / 1000,
    ),
    HomevoltSensorEntityDescription(
        key="energy_consumed",
        name="Homevolt Energy Consumed",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
        icon="mdi:battery-negative",
        value_fn=lambda data: float(data.aggregated.ems_data.energy_consumed) / 1000,
    ),
    # Device-specific sensors for each EMS device
    HomevoltSensorEntityDescription(
        key="device_status",
        name="Status",
        value_fn=lambda data, idx=0: data.ems[idx].ems_data.state_str
        if idx < len(data.ems)
        else None,
        icon_fn=lambda data, idx=0: _get_battery_icon(
            float(data.ems[idx].ems_data.soc_avg)
        )
        if idx < len(data.ems)
        else "mdi:battery-outline",
        device_specific=True,
    ),
    HomevoltSensorEntityDescription(
        key="device_power",
        name="Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement="W",
        icon="mdi:battery-sync-outline",
        value_fn=lambda data, idx=0: data.ems[idx].ems_data.power
        if idx < len(data.ems)
        else None,
        device_specific=True,
    ),
    HomevoltSensorEntityDescription(
        key="device_energy_produced",
        name="Energy Produced",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
        icon="mdi:battery-positive",
        value_fn=lambda data, idx=0: float(data.ems[idx].ems_data.energy_produced)
        / 1000
        if idx < len(data.ems)
        else None,
        device_specific=True,
    ),
    HomevoltSensorEntityDescription(
        key="device_energy_consumed",
        name="Energy Consumed",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
        icon="mdi:battery-negative",
        value_fn=lambda data, idx=0: float(data.ems[idx].ems_data.energy_consumed)
        / 1000
        if idx < len(data.ems)
        else None,
        device_specific=True,
    ),
    HomevoltSensorEntityDescription(
        key="device_error",
        name="Error",
        icon="mdi:battery-unknown",
        value_fn=lambda data, idx=0: data.ems[idx].error_str[:255]
        if idx < len(data.ems) and data.ems[idx].error_str
        else None,
        attrs_fn=lambda data, idx=0: {
            ATTR_ERROR_STR: data.ems[idx].error_str if idx < len(data.ems) else "",
        },
        device_specific=True,
    ),
    # Sensor-specific sensors for grid, solar, and load
    # Grid sensors
    HomevoltSensorEntityDescription(
        key="grid_power",
        name="Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="W",
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
        name="Energy Imported",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
        icon="mdi:transmission-tower-import",
        value_fn=lambda data: next(
            (s.energy_imported for s in data.sensors if s.type == SENSOR_TYPE_GRID),
            None,
        ),
        sensor_specific=True,
        sensor_type=SENSOR_TYPE_GRID,
    ),
    HomevoltSensorEntityDescription(
        key="grid_energy_exported",
        name="Energy Exported",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
        icon="mdi:transmission-tower-export",
        value_fn=lambda data: next(
            (s.energy_exported for s in data.sensors if s.type == SENSOR_TYPE_GRID),
            None,
        ),
        sensor_specific=True,
        sensor_type=SENSOR_TYPE_GRID,
    ),
    # Solar sensors
    HomevoltSensorEntityDescription(
        key="solar_power",
        name="Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="W",
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
        name="Energy Imported",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
        icon="mdi:solar-power-variant",
        value_fn=lambda data: next(
            (s.energy_imported for s in data.sensors if s.type == SENSOR_TYPE_SOLAR),
            None,
        ),
        sensor_specific=True,
        sensor_type=SENSOR_TYPE_SOLAR,
    ),
    HomevoltSensorEntityDescription(
        key="solar_energy_exported",
        name="Energy Exported",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
        icon="mdi:solar-power-variant-outline",
        value_fn=lambda data: next(
            (s.energy_exported for s in data.sensors if s.type == SENSOR_TYPE_SOLAR),
            None,
        ),
        sensor_specific=True,
        sensor_type=SENSOR_TYPE_SOLAR,
    ),
    # Load sensors
    HomevoltSensorEntityDescription(
        key="load_power",
        name="Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="W",
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
        name="Energy Imported",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
        icon="mdi:home-import-outline",
        value_fn=lambda data: next(
            (s.energy_imported for s in data.sensors if s.type == SENSOR_TYPE_LOAD),
            None,
        ),
        sensor_specific=True,
        sensor_type=SENSOR_TYPE_LOAD,
    ),
    HomevoltSensorEntityDescription(
        key="load_energy_exported",
        name="Energy Exported",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
        icon="mdi:home-export-outline",
        value_fn=lambda data: next(
            (s.energy_exported for s in data.sensors if s.type == SENSOR_TYPE_LOAD),
            None,
        ),
        sensor_specific=True,
        sensor_type=SENSOR_TYPE_LOAD,
    ),
)


class HomevoltSensor(CoordinatorEntity[HomevoltData], SensorEntity):
    """Representation of a Homevolt sensor."""

    entity_description: HomevoltSensorEntityDescription

    def __init__(
        self,
        coordinator: HomevoltDataUpdateCoordinator,
        description: HomevoltSensorEntityDescription,
        ems_index: int | None = None,
        sensor_index: int | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self.ems_index = ems_index
        self.sensor_index = sensor_index

        # Create a unique ID based on the device properties if available
        if ems_index is not None and coordinator.data and coordinator.data.ems:
            try:
                # Use the ecu_id for a consistent unique ID
                ems_device = coordinator.data.ems[ems_index]
                ecu_id = ems_device.ecu_id or f"unknown_{ems_index}"
                self._attr_unique_id = f"{DOMAIN}_{description.key}_ems_{ecu_id}"
            except IndexError:
                # Fallback to a generic unique ID if we can't get the ecu_id
                self._attr_unique_id = f"{DOMAIN}_{description.key}_ems_{ems_index}"
        elif sensor_index is not None and coordinator.data and coordinator.data.sensors:
            try:
                # Use the euid for a consistent unique ID
                sensor_data = coordinator.data.sensors[sensor_index]
                euid = sensor_data.euid or f"unknown_{sensor_index}"
                self._attr_unique_id = f"{DOMAIN}_{description.key}_sensor_{euid}"
            except IndexError:
                # Fallback to a generic unique ID if we can't get the euid
                self._attr_unique_id = (
                    f"{DOMAIN}_{description.key}_sensor_{sensor_index}"
                )
        else:
            # For aggregated sensors, use the host for a consistent unique ID
            host = coordinator.resource.split("://")[1].split("/")[0]
            self._attr_unique_id = f"{DOMAIN}_{description.key}_{host}"

        self._attr_device_info = self.device_info

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this Homevolt device."""
        host = self.coordinator.resource.split("://")[1].split("/")[0]
        main_device_id = f"homevolt_{host}"

        if (
            self.ems_index is not None
            and self.coordinator.data
            and self.coordinator.data.ems
        ):
            return self._get_ems_device_info(main_device_id)
        if (
            self.sensor_index is not None
            and self.coordinator.data
            and self.coordinator.data.sensors
        ):
            return self._get_sensor_device_info(main_device_id)

        # For aggregated sensors
        return DeviceInfo(
            identifiers={(DOMAIN, main_device_id)},
            name=f"Homevolt Local ({host})",
            manufacturer="Homevolt",
            model="Energy Management System",
            entry_type=DeviceEntryType.SERVICE,
        )

    def _get_ems_device_info(self, main_device_id: str) -> DeviceInfo:
        """Return device information for an EMS device."""
        try:
            ems_device = self.coordinator.data.ems[self.ems_index]
            ecu_id = ems_device.ecu_id or f"unknown_{self.ems_index}"
            serial_number = (
                ems_device.inv_info.serial_number if ems_device.inv_info else ""
            )
            fw_version = ems_device.ems_info.fw_version if ems_device.ems_info else ""

            return DeviceInfo(
                identifiers={(DOMAIN, f"ems_{ecu_id}")},
                name=f"Homevolt EMS {ecu_id}",
                manufacturer="Homevolt",
                model=f"Energy Management System {fw_version}",
                entry_type=DeviceEntryType.SERVICE,
                via_device=(DOMAIN, main_device_id),
                sw_version=fw_version,
                hw_version=serial_number,
            )
        except IndexError:
            return DeviceInfo(
                identifiers={(DOMAIN, f"ems_unknown_{self.ems_index}")},
                name=f"Homevolt EMS {self.ems_index + 1}",
                manufacturer="Homevolt",
                model="Energy Management System",
                entry_type=DeviceEntryType.SERVICE,
                via_device=(DOMAIN, main_device_id),
            )

    def _get_sensor_device_info(self, main_device_id: str) -> DeviceInfo:
        """Return device information for a sensor device."""
        try:
            sensor_data = self.coordinator.data.sensors[self.sensor_index]
            sensor_type = sensor_data.type or "unknown"
            node_id = sensor_data.node_id
            euid = sensor_data.euid or "unknown"
            sensor_type_name = sensor_type.capitalize()

            return DeviceInfo(
                identifiers={(DOMAIN, f"sensor_{euid}")},
                name=f"Homevolt {sensor_type_name}",
                manufacturer="Homevolt",
                model=f"{sensor_type_name} Sensor (Node {node_id})",
                entry_type=DeviceEntryType.SERVICE,
                via_device=(DOMAIN, main_device_id),
            )
        except IndexError:
            return DeviceInfo(
                identifiers={(DOMAIN, f"sensor_unknown_{self.sensor_index}")},
                name=f"Homevolt Sensor {self.sensor_index + 1}",
                manufacturer="Homevolt",
                model="Sensor",
                entry_type=DeviceEntryType.SERVICE,
                via_device=(DOMAIN, main_device_id),
            )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.coordinator.data is None:
            self._attr_native_value = None
            self._attr_extra_state_attributes = {}
            self.async_write_ha_state()
            return

        try:
            data = self.coordinator.data
            self._update_sensor_value(data)
            self._update_sensor_icon(data)
            self._update_sensor_attributes(data)

        except (KeyError, TypeError, IndexError, ValueError, AttributeError) as err:
            _LOGGER.error(
                "Error extracting sensor data for %s: %s",
                self.entity_description.name,
                err,
            )
            self._attr_native_value = None
            self._attr_extra_state_attributes = {}

        self.async_write_ha_state()

    def _update_sensor_value(self, data: HomevoltData):
        """Update the sensor's value."""
        if self.entity_description.value_fn:
            if self.ems_index is not None:
                self._attr_native_value = self.entity_description.value_fn(
                    data, self.ems_index
                )
            else:
                self._attr_native_value = self.entity_description.value_fn(data)

    def _update_sensor_icon(self, data: HomevoltData):
        """Update the sensor's icon."""
        if self.entity_description.icon_fn:
            if self.ems_index is not None:
                self._attr_icon = self.entity_description.icon_fn(data, self.ems_index)
            else:
                self._attr_icon = self.entity_description.icon_fn(data)

    def _update_sensor_attributes(self, data: HomevoltData):
        """Update the sensor's attributes."""
        if self.entity_description.attrs_fn:
            if self.ems_index is not None:
                self._attr_extra_state_attributes = self.entity_description.attrs_fn(
                    data, self.ems_index
                )
            else:
                self._attr_extra_state_attributes = self.entity_description.attrs_fn(
                    data
                )


def _create_device_sensors(
    coordinator: HomevoltDataUpdateCoordinator,
) -> list[HomevoltSensor]:
    """Create device-specific sensors."""
    sensors = []
    if not (coordinator.data and coordinator.data.ems):
        return sensors

    for idx, _ in enumerate(coordinator.data.ems):
        for description in SENSOR_DESCRIPTIONS:
            if description.device_specific:
                sensors.append(HomevoltSensor(coordinator, description, idx))
    return sensors


def _create_type_sensors(
    coordinator: HomevoltDataUpdateCoordinator,
) -> list[HomevoltSensor]:
    """Create sensor-specific sensors."""
    sensors = []
    if not (coordinator.data and coordinator.data.sensors):
        return sensors

    available_types = {
        s.type for s in coordinator.data.sensors if s.available is not False
    }

    for description in SENSOR_DESCRIPTIONS:
        if (
            description.sensor_specific
            and description.sensor_type in available_types
        ):
            for idx, sensor in enumerate(coordinator.data.sensors):
                if (
                    sensor.type == description.sensor_type
                    and sensor.available is not False
                ):
                    sensors.append(HomevoltSensor(coordinator, description, None, idx))
                    break
    return sensors


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Homevolt Local sensor based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    sensors = [
        HomevoltSensor(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
        if not description.device_specific and not description.sensor_specific
    ]

    sensors.extend(_create_device_sensors(coordinator))
    sensors.extend(_create_type_sensors(coordinator))

    async_add_entities(sensors)

        attrs_fn=lambda data, idx=0: {
            ATTR_ERROR_STR: data.ems[idx].error_str if idx < len(data.ems) else "",
        },
        device_specific=True,
    ),
    # Sensor-specific sensors for grid, solar, and load
    # Grid sensors
    HomevoltSensorEntityDescription(
        key="grid_power",
        name="Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="W",
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
        name="Energy Imported",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
        icon="mdi:transmission-tower-import",
        value_fn=lambda data: next(
            (s.energy_imported for s in data.sensors if s.type == SENSOR_TYPE_GRID),
            None,
        ),
        sensor_specific=True,
        sensor_type=SENSOR_TYPE_GRID,
    ),
    HomevoltSensorEntityDescription(
        key="grid_energy_exported",
        name="Energy Exported",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
        icon="mdi:transmission-tower-export",
        value_fn=lambda data: next(
            (s.energy_exported for s in data.sensors if s.type == SENSOR_TYPE_GRID),
            None,
        ),
        sensor_specific=True,
        sensor_type=SENSOR_TYPE_GRID,
    ),
    # Solar sensors
    HomevoltSensorEntityDescription(
        key="solar_power",
        name="Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="W",
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
        name="Energy Imported",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
        icon="mdi:solar-power-variant",
        value_fn=lambda data: next(
            (s.energy_imported for s in data.sensors if s.type == SENSOR_TYPE_SOLAR),
            None,
        ),
        sensor_specific=True,
        sensor_type=SENSOR_TYPE_SOLAR,
    ),
    HomevoltSensorEntityDescription(
        key="solar_energy_exported",
        name="Energy Exported",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
        icon="mdi:solar-power-variant-outline",
        value_fn=lambda data: next(
            (s.energy_exported for s in data.sensors if s.type == SENSOR_TYPE_SOLAR),
            None,
        ),
        sensor_specific=True,
        sensor_type=SENSOR_TYPE_SOLAR,
    ),
    # Load sensors
    HomevoltSensorEntityDescription(
        key="load_power",
        name="Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="W",
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
        name="Energy Imported",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
        icon="mdi:home-import-outline",
        value_fn=lambda data: next(
            (s.energy_imported for s in data.sensors if s.type == SENSOR_TYPE_LOAD),
            None,
        ),
        sensor_specific=True,
        sensor_type=SENSOR_TYPE_LOAD,
    ),
    HomevoltSensorEntityDescription(
        key="load_energy_exported",
        name="Energy Exported",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
        icon="mdi:home-export-outline",
        value_fn=lambda data: next(
            (s.energy_exported for s in data.sensors if s.type == SENSOR_TYPE_LOAD),
            None,
        ),
        sensor_specific=True,
        sensor_type=SENSOR_TYPE_LOAD,
    ),
)


class HomevoltSensor(CoordinatorEntity[HomevoltData], SensorEntity):
    """Representation of a Homevolt sensor."""

    entity_description: HomevoltSensorEntityDescription

    def __init__(
        self,
        coordinator: HomevoltDataUpdateCoordinator,
        description: HomevoltSensorEntityDescription,
        ems_index: int | None = None,
        sensor_index: int | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self.ems_index = ems_index
        self.sensor_index = sensor_index

        # Create a unique ID based on the device properties if available
        if ems_index is not None and coordinator.data and coordinator.data.ems:
            try:
                # Use the ecu_id for a consistent unique ID
                ems_device = coordinator.data.ems[ems_index]
                ecu_id = ems_device.ecu_id or f"unknown_{ems_index}"
                self._attr_unique_id = f"{DOMAIN}_{description.key}_ems_{ecu_id}"
            except IndexError:
                # Fallback to a generic unique ID if we can't get the ecu_id
                self._attr_unique_id = f"{DOMAIN}_{description.key}_ems_{ems_index}"
        elif sensor_index is not None and coordinator.data and coordinator.data.sensors:
            try:
                # Use the euid for a consistent unique ID
                sensor_data = coordinator.data.sensors[sensor_index]
                euid = sensor_data.euid or f"unknown_{sensor_index}"
                self._attr_unique_id = f"{DOMAIN}_{description.key}_sensor_{euid}"
            except IndexError:
                # Fallback to a generic unique ID if we can't get the euid
                self._attr_unique_id = (
                    f"{DOMAIN}_{description.key}_sensor_{sensor_index}"
                )
        else:
            # For aggregated sensors, use the host for a consistent unique ID
            host = coordinator.resource.split("://")[1].split("/")[0]
            self._attr_unique_id = f"{DOMAIN}_{description.key}_{host}"

        self._attr_device_info = self.device_info

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this Homevolt device."""
        host = self.coordinator.resource.split("://")[1].split("/")[0]
        main_device_id = f"homevolt_{host}"

        if self.ems_index is not None and self.coordinator.data and self.coordinator.data.ems:
            return self._get_ems_device_info(main_device_id)
        if (
            self.sensor_index is not None
            and self.coordinator.data
            and self.coordinator.data.sensors
        ):
            return self._get_sensor_device_info(main_device_id)

        # For aggregated sensors
        return DeviceInfo(
            identifiers={(DOMAIN, main_device_id)},
            name=f"Homevolt Local ({host})",
            manufacturer="Homevolt",
            model="Energy Management System",
            entry_type=DeviceEntryType.SERVICE,
        )

    def _get_ems_device_info(self, main_device_id: str) -> DeviceInfo:
        """Return device information for an EMS device."""
        try:
            ems_device = self.coordinator.data.ems[self.ems_index]
            ecu_id = ems_device.ecu_id or f"unknown_{self.ems_index}"
            serial_number = (
                ems_device.inv_info.serial_number if ems_device.inv_info else ""
            )
            fw_version = ems_device.ems_info.fw_version if ems_device.ems_info else ""

            return DeviceInfo(
                identifiers={(DOMAIN, f"ems_{ecu_id}")},
                name=f"Homevolt EMS {ecu_id}",
                manufacturer="Homevolt",
                model=f"Energy Management System {fw_version}",
                entry_type=DeviceEntryType.SERVICE,
                via_device=(DOMAIN, main_device_id),
                sw_version=fw_version,
                hw_version=serial_number,
            )
        except IndexError:
            return DeviceInfo(
                identifiers={(DOMAIN, f"ems_unknown_{self.ems_index}")},
                name=f"Homevolt EMS {self.ems_index + 1}",
                manufacturer="Homevolt",
                model="Energy Management System",
                entry_type=DeviceEntryType.SERVICE,
                via_device=(DOMAIN, main_device_id),
            )

    def _get_sensor_device_info(self, main_device_id: str) -> DeviceInfo:
        """Return device information for a sensor device."""
        try:
            sensor_data = self.coordinator.data.sensors[self.sensor_index]
            sensor_type = sensor_data.type or "unknown"
            node_id = sensor_data.node_id
            euid = sensor_data.euid or "unknown"
            sensor_type_name = sensor_type.capitalize()

            return DeviceInfo(
                identifiers={(DOMAIN, f"sensor_{euid}")},
                name=f"Homevolt {sensor_type_name}",
                manufacturer="Homevolt",
                model=f"{sensor_type_name} Sensor (Node {node_id})",
                entry_type=DeviceEntryType.SERVICE,
                via_device=(DOMAIN, main_device_id),
            )
        except IndexError:
            return DeviceInfo(
                identifiers={(DOMAIN, f"sensor_unknown_{self.sensor_index}")},
                name=f"Homevolt Sensor {self.sensor_index + 1}",
                manufacturer="Homevolt",
                model="Sensor",
                entry_type=DeviceEntryType.SERVICE,
                via_device=(DOMAIN, main_device_id),
            )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.coordinator.data is None:
            self._attr_native_value = None
            self._attr_extra_state_attributes = {}
            self.async_write_ha_state()
            return

        try:
            data = self.coordinator.data
            self._update_sensor_value(data)
            self._update_sensor_icon(data)
            self._update_sensor_attributes(data)

        except (KeyError, TypeError, IndexError, ValueError, AttributeError) as err:
            _LOGGER.error(
                "Error extracting sensor data for %s: %s",
                self.entity_description.name,
                err,
            )
            self._attr_native_value = None
            self._attr_extra_state_attributes = {}

        self.async_write_ha_state()

    def _update_sensor_value(self, data: HomevoltData):
        """Update the sensor's value."""
        if self.entity_description.value_fn:
            if self.ems_index is not None:
                self._attr_native_value = self.entity_description.value_fn(
                    data, self.ems_index
                )
            else:
                self._attr_native_value = self.entity_description.value_fn(data)

    def _update_sensor_icon(self, data: HomevoltData):
        """Update the sensor's icon."""
        if self.entity_description.icon_fn:
            if self.ems_index is not None:
                self._attr_icon = self.entity_description.icon_fn(data, self.ems_index)
            else:
                self._attr_icon = self.entity_description.icon_fn(data)

    def _update_sensor_attributes(self, data: HomevoltData):
        """Update the sensor's attributes."""
        if self.entity_description.attrs_fn:
            if self.ems_index is not None:
                self._attr_extra_state_attributes = self.entity_description.attrs_fn(
                    data, self.ems_index
                )
            else:
                self._attr_extra_state_attributes = self.entity_description.attrs_fn(
                    data
                )


def _create_device_sensors(
    coordinator: HomevoltDataUpdateCoordinator,
) -> list[HomevoltSensor]:
    """Create device-specific sensors."""
    sensors = []
    if not (coordinator.data and coordinator.data.ems):
        return sensors

    for idx, _ in enumerate(coordinator.data.ems):
        for description in SENSOR_DESCRIPTIONS:
            if description.device_specific:
                sensors.append(HomevoltSensor(coordinator, description, idx))
    return sensors


def _create_type_sensors(
    coordinator: HomevoltDataUpdateCoordinator,
) -> list[HomevoltSensor]:
    """Create sensor-specific sensors."""
    sensors = []
    if not (coordinator.data and coordinator.data.sensors):
        return sensors

    available_types = {
        s.type for s in coordinator.data.sensors if s.available is not False
    }

    for description in SENSOR_DESCRIPTIONS:
        if (
            description.sensor_specific
            and description.sensor_type in available_types
        ):
            for idx, sensor in enumerate(coordinator.data.sensors):
                if (
                    sensor.type == description.sensor_type
                    and sensor.available is not False
                ):
                    sensors.append(HomevoltSensor(coordinator, description, None, idx))
                    break
    return sensors


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Homevolt Local sensor based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    sensors = [
        HomevoltSensor(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
        if not description.device_specific and not description.sensor_specific
    ]

    sensors.extend(_create_device_sensors(coordinator))
    sensors.extend(_create_type_sensors(coordinator))

    async_add_entities(sensors)
