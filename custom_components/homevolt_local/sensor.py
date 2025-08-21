"""Sensor platform for Homevolt Local integration."""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Union

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from dataclasses import dataclass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HomevoltDataUpdateCoordinator
from .models import HomevoltData, EmsDevice, SensorData
from .const import (
    ATTR_AGGREGATED,
    ATTR_AVAILABLE,
    ATTR_ECU_ID,
    ATTR_EMS,
    ATTR_EMS_DATA,
    ATTR_EMS_INFO,
    ATTR_ENERGY_CONSUMED,
    ATTR_ENERGY_EXPORTED,
    ATTR_ENERGY_IMPORTED,
    ATTR_ENERGY_PRODUCED,
    ATTR_ERROR_STR,
    ATTR_EUID,
    ATTR_FW_VERSION,
    ATTR_INV_INFO,
    ATTR_NODE_ID,
    ATTR_PHASE,
    ATTR_POWER,
    ATTR_SENSORS,
    ATTR_SERIAL_NUMBER,
    ATTR_SOC_AVG,
    ATTR_STATE_STR,
    ATTR_TIMESTAMP,
    ATTR_TOTAL_POWER,
    ATTR_TYPE,
    BMS_DATA_INDEX_DEVICE,
    BMS_DATA_INDEX_TOTAL,
    DOMAIN,
    SENSOR_INDEX_GRID,
    SENSOR_INDEX_LOAD,
    SENSOR_INDEX_SOLAR,
    SENSOR_TYPE_GRID,
    SENSOR_TYPE_LOAD,
    SENSOR_TYPE_SOLAR,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class HomevoltSensorEntityDescription(SensorEntityDescription):
    """Describes Homevolt sensor entity."""

    value_fn: Callable[[Union[HomevoltData, Dict[str, Any]]], Any] = None
    icon_fn: Callable[[Union[HomevoltData, Dict[str, Any]]], str] = None
    attrs_fn: Callable[[Union[HomevoltData, Dict[str, Any]]], Dict[str, Any]] = None
    device_specific: bool = False  # Whether this sensor is specific to a device in the ems array
    sensor_specific: bool = False  # Whether this sensor is specific to a device in the sensors array
    sensor_type: str = None  # The type of sensor this entity is for (grid, solar, load)


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
            ATTR_SENSORS: [sensor.__dict__ for sensor in data.sensors] if data.sensors else [],
        },
    ),
    HomevoltSensorEntityDescription(
        key="ems_error",
        name="Homevolt Error",
        icon="mdi:battery-unknown",
        value_fn=lambda data: data.aggregated.error_str[:255] if data.aggregated.error_str else None,
        attrs_fn=lambda data: {
            ATTR_ERROR_STR: data.aggregated.error_str,
        },
    ),
    HomevoltSensorEntityDescription(
        key="battery_soc",
        name="Homevolt battery SoC",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement="%",
        value_fn=lambda data, idx=0: float(data.ems[idx].bms_data[BMS_DATA_INDEX_DEVICE].soc) / 100 if idx < len(data.ems) else None,
        device_specific=True,
    ),
    HomevoltSensorEntityDescription(
        key="total_soc",
        name="Homevolt Total SoC",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement="%",
        value_fn=lambda data: float(data.aggregated.bms_data[BMS_DATA_INDEX_TOTAL].soc) / 100 if data.aggregated.bms_data and len(data.aggregated.bms_data) > BMS_DATA_INDEX_TOTAL else None,
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
        value_fn=lambda data, idx=0: data.ems[idx].ems_data.state_str if idx < len(data.ems) else None,
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
        value_fn=lambda data, idx=0: data.ems[idx].ems_data.power if idx < len(data.ems) else None,
        device_specific=True,
    ),
    HomevoltSensorEntityDescription(
        key="device_energy_produced",
        name="Energy Produced",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
        icon="mdi:battery-positive",
        value_fn=lambda data, idx=0: float(data.ems[idx].ems_data.energy_produced) / 1000 if idx < len(data.ems) else None,
        device_specific=True,
    ),
    HomevoltSensorEntityDescription(
        key="device_energy_consumed",
        name="Energy Consumed",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
        icon="mdi:battery-negative",
        value_fn=lambda data, idx=0: float(data.ems[idx].ems_data.energy_consumed) / 1000 if idx < len(data.ems) else None,
        device_specific=True,
    ),
    HomevoltSensorEntityDescription(
        key="device_error",
        name="Error",
        icon="mdi:battery-unknown",
        value_fn=lambda data, idx=0: data.ems[idx].error_str[:255] if idx < len(data.ems) and data.ems[idx].error_str else None,
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
        value_fn=lambda data: next((s.total_power for s in data.sensors if s.type == SENSOR_TYPE_GRID), None),
        attrs_fn=lambda data: {
            ATTR_PHASE: next((s.phase for s in data.sensors if s.type == SENSOR_TYPE_GRID), None),
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
        value_fn=lambda data: next((s.energy_imported for s in data.sensors if s.type == SENSOR_TYPE_GRID), None),
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
        value_fn=lambda data: next((s.energy_exported for s in data.sensors if s.type == SENSOR_TYPE_GRID), None),
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
        value_fn=lambda data: next((s.total_power for s in data.sensors if s.type == SENSOR_TYPE_SOLAR), None),
        attrs_fn=lambda data: {
            ATTR_PHASE: next((s.phase for s in data.sensors if s.type == SENSOR_TYPE_SOLAR), None),
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
        value_fn=lambda data: next((s.energy_imported for s in data.sensors if s.type == SENSOR_TYPE_SOLAR), None),
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
        value_fn=lambda data: next((s.energy_exported for s in data.sensors if s.type == SENSOR_TYPE_SOLAR), None),
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
        value_fn=lambda data: next((s.total_power for s in data.sensors if s.type == SENSOR_TYPE_LOAD), None),
        attrs_fn=lambda data: {
            ATTR_PHASE: next((s.phase for s in data.sensors if s.type == SENSOR_TYPE_LOAD), None),
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
        value_fn=lambda data: next((s.energy_imported for s in data.sensors if s.type == SENSOR_TYPE_LOAD), None),
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
        value_fn=lambda data: next((s.energy_exported for s in data.sensors if s.type == SENSOR_TYPE_LOAD), None),
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
        ems_index: int = None,
        sensor_index: int = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self.ems_index = ems_index
        self.sensor_index = sensor_index

        # Create a unique ID based on the device properties if available
        if ems_index is not None and coordinator.data and coordinator.data.ems:
            try:
                # Use the ecu_id for a consistent unique ID across different IP addresses
                ems_device = coordinator.data.ems[ems_index]
                ecu_id = ems_device.ecu_id or f"unknown_{ems_index}"
                self._attr_unique_id = f"{DOMAIN}_{description.key}_ems_{ecu_id}"
            except (IndexError):
                # Fallback to a generic unique ID if we can't get the ecu_id
                self._attr_unique_id = f"{DOMAIN}_{description.key}_ems_{ems_index}"
        elif sensor_index is not None and coordinator.data and coordinator.data.sensors:
            try:
                # Use the euid for a consistent unique ID across different IP addresses
                sensor_data = coordinator.data.sensors[sensor_index]
                euid = sensor_data.euid or f"unknown_{sensor_index}"
                self._attr_unique_id = f"{DOMAIN}_{description.key}_sensor_{euid}"
            except (IndexError):
                # Fallback to a generic unique ID if we can't get the euid
                self._attr_unique_id = f"{DOMAIN}_{description.key}_sensor_{sensor_index}"
        else:
            # For aggregated sensors, use the host from the resource URL for a consistent unique ID
            host = coordinator.resource.split("://")[1].split("/")[0]
            self._attr_unique_id = f"{DOMAIN}_{description.key}_{host}"

        self._attr_device_info = self.device_info

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this Homevolt device."""
        # Main aggregated device ID - use the host from the resource URL to make it consistent
        # across different config entries for the same physical system
        host = self.coordinator.resource.split("://")[1].split("/")[0]
        main_device_id = f"homevolt_{host}"

        if self.ems_index is not None and self.coordinator.data and self.coordinator.data.ems:
            # Get device-specific information from the ems data
            try:
                ems_device = self.coordinator.data.ems[self.ems_index]
                ecu_id = ems_device.ecu_id or f"unknown_{self.ems_index}"
                serial_number = ems_device.inv_info.serial_number if ems_device.inv_info else ""

                # Try to get more detailed information for the device name
                fw_version = ems_device.ems_info.fw_version if ems_device.ems_info else ""

                # Use the ecu_id as the unique identifier, which should be consistent
                # across different IP addresses for the same physical device
                return DeviceInfo(
                    identifiers={(DOMAIN, f"ems_{ecu_id}")},
                    name=f"Homevolt EMS {ecu_id}",
                    manufacturer="Homevolt",
                    model=f"Energy Management System {fw_version}",
                    entry_type=DeviceEntryType.SERVICE,
                    via_device=(DOMAIN, main_device_id),  # Link to the main device
                    sw_version=fw_version,
                    hw_version=serial_number,
                )
            except (IndexError):
                # Fallback to a generic device info if we can't get specific info
                return DeviceInfo(
                    identifiers={(DOMAIN, f"ems_unknown_{self.ems_index}")},
                    name=f"Homevolt EMS {self.ems_index + 1}",
                    manufacturer="Homevolt",
                    model="Energy Management System",
                    entry_type=DeviceEntryType.SERVICE,
                    via_device=(DOMAIN, main_device_id),  # Link to the main device
                )
        elif self.sensor_index is not None and self.coordinator.data and self.coordinator.data.sensors:
            # Get device-specific information from the sensors data
            try:
                sensor_data = self.coordinator.data.sensors[self.sensor_index]
                sensor_type = sensor_data.type or "unknown"
                node_id = sensor_data.node_id
                euid = sensor_data.euid or "unknown"

                # Capitalize the first letter of the sensor type for the name
                sensor_type_name = sensor_type.capitalize()

                # Use the euid as the unique identifier, which should be consistent
                # across different IP addresses for the same physical sensor
                return DeviceInfo(
                    identifiers={(DOMAIN, f"sensor_{euid}")},
                    name=f"Homevolt {sensor_type_name}",
                    manufacturer="Homevolt",
                    model=f"{sensor_type_name} Sensor (Node {node_id})",
                    entry_type=DeviceEntryType.SERVICE,
                    via_device=(DOMAIN, main_device_id),  # Link to the main device
                )
            except (IndexError):
                # Fallback to a generic device info if we can't get specific info
                return DeviceInfo(
                    identifiers={(DOMAIN, f"sensor_unknown_{self.sensor_index}")},
                    name=f"Homevolt Sensor {self.sensor_index + 1}",
                    manufacturer="Homevolt",
                    model="Sensor",
                    entry_type=DeviceEntryType.SERVICE,
                    via_device=(DOMAIN, main_device_id),  # Link to the main device
                )
        else:
            # For aggregated sensors or if no ems_index or sensor_index is provided
            return DeviceInfo(
                identifiers={(DOMAIN, main_device_id)},
                name=f"Homevolt Local ({host})",
                manufacturer="Homevolt",
                model="Energy Management System",
                entry_type=DeviceEntryType.SERVICE,
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

            # Check if this is a device-specific sensor and if the device exists
            if self.ems_index is not None and data.ems:
                # Verify the device index is valid
                if len(data.ems) <= self.ems_index:
                    _LOGGER.error(
                        "Device index %s is out of range for %s (only %s devices available)",
                        self.ems_index,
                        self.entity_description.name,
                        len(data.ems),
                    )
                    self._attr_native_value = None
                    self._attr_extra_state_attributes = {}
                    self.async_write_ha_state()
                    return

            # Check if this is a sensor-specific sensor and if the sensor exists
            elif self.sensor_index is not None and data.sensors:
                # Verify the sensor index is valid
                if len(data.sensors) <= self.sensor_index:
                    _LOGGER.error(
                        "Sensor index %s is out of range for %s (only %s sensors available)",
                        self.sensor_index,
                        self.entity_description.name,
                        len(data.sensors),
                    )
                    self._attr_native_value = None
                    self._attr_extra_state_attributes = {}
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
                            self._attr_extra_state_attributes = {}
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
                    self._attr_extra_state_attributes = self.entity_description.attrs_fn(data)
                elif self.sensor_index is not None:
                    # For sensor-specific sensors, pass the sensor index to the attrs_fn
                    self._attr_extra_state_attributes = self.entity_description.attrs_fn(data)
                else:
                    # For aggregated sensors, just pass the data
                    self._attr_extra_state_attributes = self.entity_description.attrs_fn(data)

        except (KeyError, TypeError, IndexError, ValueError, AttributeError) as err:
            _LOGGER.error("Error extracting sensor data for %s: %s", self.entity_description.name, err)
            self._attr_native_value = None
            self._attr_extra_state_attributes = {}

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
        ems_data = coordinator.data.ems

        # Create device-specific sensors for each device in the ems array
        for idx, _ in enumerate(ems_data):
            for description in SENSOR_DESCRIPTIONS:
                if description.device_specific:
                    # Create a modified value_fn that includes the device index
                    if description.value_fn:
                        # Create a copy of the description with all necessary attributes
                        # Include wrapper functions for value_fn, icon_fn, and attrs_fn in the constructor
                        original_value_fn = description.value_fn
                        value_fn_wrapper = lambda data, orig_fn=original_value_fn, device_idx=idx: orig_fn(data, device_idx)

                        # Prepare icon_fn wrapper if it exists
                        icon_fn_wrapper = None
                        if description.icon_fn:
                            original_icon_fn = description.icon_fn
                            icon_fn_wrapper = lambda data, orig_fn=original_icon_fn, device_idx=idx: orig_fn(data, device_idx)

                        # Prepare attrs_fn wrapper if it exists
                        attrs_fn_wrapper = None
                        if description.attrs_fn:
                            original_attrs_fn = description.attrs_fn
                            attrs_fn_wrapper = lambda data, orig_fn=original_attrs_fn, device_idx=idx: orig_fn(data, device_idx)

                        # Create the modified description with all wrappers included in the constructor
                        modified_description = HomevoltSensorEntityDescription(
                            key=description.key,
                            name=description.name,
                            device_class=description.device_class,
                            native_unit_of_measurement=description.native_unit_of_measurement,
                            icon=description.icon,
                            device_specific=description.device_specific,
                            value_fn=value_fn_wrapper,
                            icon_fn=icon_fn_wrapper,
                            attrs_fn=attrs_fn_wrapper,
                        )

                        sensors.append(HomevoltSensor(coordinator, modified_description, idx))
                    else:
                        sensors.append(HomevoltSensor(coordinator, description, idx))

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
                        if sensor.type == description.sensor_type and sensor.available is not False:
                            # Create a sensor for this type
                            sensors.append(HomevoltSensor(coordinator, description, None, idx))
                            break

    async_add_entities(sensors)
