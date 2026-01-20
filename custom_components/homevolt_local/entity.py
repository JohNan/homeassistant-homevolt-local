"""The Homevolt Local integration base entity."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

if TYPE_CHECKING:
    from .coordinator import HomevoltDataUpdateCoordinator
    from .models import HomevoltData

_LOGGER = logging.getLogger(__name__)

MANUFACTURER = "Homevolt"


class HomevoltEntity(CoordinatorEntity["HomevoltDataUpdateCoordinator"]):
    """Base class for Homevolt entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HomevoltDataUpdateCoordinator,
        ems_index: int | None = None,
        sensor_index: int | None = None,
        bms_index: int | None = None,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.ems_index = ems_index
        self.sensor_index = sensor_index
        self.bms_index = bms_index

    @property
    def main_device_id(self) -> str:
        """Return the main device ID for consistent identification."""
        return f"homevolt_{self.coordinator.get_main_device_id()}"

    @property
    def data(self) -> HomevoltData | None:
        """Return the coordinator data."""
        return self.coordinator.data

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this Homevolt device."""
        main_device_id = self.main_device_id

        # BMS (Battery) device - sub-device of the Inverter
        if self.bms_index is not None and self.ems_index is not None:
            return self._get_bms_device_info(main_device_id)
        elif self.ems_index is not None:
            return self._get_ems_device_info(main_device_id)
        elif self.sensor_index is not None:
            return self._get_sensor_device_info(main_device_id)
        else:
            return self._get_system_device_info(main_device_id)

    def _get_bms_device_info(self, main_device_id: str) -> DeviceInfo:
        """Return device info for a BMS (battery) device."""
        if self.ems_index is None or self.bms_index is None:
            return self._get_system_device_info(main_device_id)

        if not self.coordinator.data or not self.coordinator.data.ems:
            return self._get_fallback_bms_device_info(main_device_id)

        ems_index = self.ems_index
        bms_index = self.bms_index

        try:
            ems_device = self.coordinator.data.ems[ems_index]
            ecu_id = ems_device.ecu_id or f"unknown_{ems_index}"
            inverter_device_id = f"ems_{ecu_id}"

            # Get BMS info for this battery
            bms_info = (
                ems_device.bms_info[bms_index]
                if ems_device.bms_info and len(ems_device.bms_info) > bms_index
                else None
            )
            bms_serial = (
                bms_info.serial_number
                if bms_info and bms_info.serial_number
                else f"bms_{bms_index}"
            )
            bms_fw = bms_info.fw_version if bms_info else ""
            bms_id = bms_info.id + 1 if bms_info else bms_index + 1
            inverter_num = ems_index + 1

            return DeviceInfo(
                identifiers={(DOMAIN, f"bms_{ecu_id}_{bms_serial}")},
                translation_key="battery",
                translation_placeholders={
                    "inverter_num": str(inverter_num),
                    "battery_num": str(bms_id),
                },
                manufacturer=MANUFACTURER,
                model="Battery Module",
                entry_type=DeviceEntryType.SERVICE,
                via_device=(DOMAIN, inverter_device_id),
                sw_version=bms_fw,
                hw_version=bms_serial,
            )
        except IndexError:
            return self._get_fallback_bms_device_info(main_device_id)

    def _get_fallback_bms_device_info(self, main_device_id: str) -> DeviceInfo:
        """Return fallback device info for a BMS device."""
        ems_index = self.ems_index if self.ems_index is not None else 0
        bms_index = self.bms_index if self.bms_index is not None else 0

        return DeviceInfo(
            identifiers={(DOMAIN, f"bms_unknown_{ems_index}_{bms_index}")},
            translation_key="battery",
            translation_placeholders={
                "inverter_num": str(ems_index + 1),
                "battery_num": str(bms_index + 1),
            },
            manufacturer=MANUFACTURER,
            model="Battery Module",
            entry_type=DeviceEntryType.SERVICE,
            via_device=(DOMAIN, main_device_id),
        )

    def _get_ems_device_info(self, main_device_id: str) -> DeviceInfo:
        """Return device info for an EMS (inverter) device."""
        if self.ems_index is None:
            return self._get_system_device_info(main_device_id)

        if not self.coordinator.data or not self.coordinator.data.ems:
            return self._get_fallback_ems_device_info(main_device_id)

        ems_index = self.ems_index

        try:
            ems_device = self.coordinator.data.ems[ems_index]
            ecu_id = ems_device.ecu_id or f"unknown_{ems_index}"
            serial_number = (
                ems_device.inv_info.serial_number if ems_device.inv_info else ""
            )
            fw_version = ems_device.ems_info.fw_version if ems_device.ems_info else ""

            return DeviceInfo(
                identifiers={(DOMAIN, f"ems_{ecu_id}")},
                translation_key="inverter",
                translation_placeholders={"inverter_num": str(ems_index + 1)},
                manufacturer=MANUFACTURER,
                model=f"Energy Management System {fw_version}",
                entry_type=DeviceEntryType.SERVICE,
                via_device=(DOMAIN, main_device_id),
                sw_version=fw_version,
                hw_version=serial_number,
            )
        except IndexError:
            return self._get_fallback_ems_device_info(main_device_id)

    def _get_fallback_ems_device_info(self, main_device_id: str) -> DeviceInfo:
        """Return fallback device info for an EMS device."""
        ems_index = self.ems_index if self.ems_index is not None else 0

        return DeviceInfo(
            identifiers={(DOMAIN, f"ems_unknown_{ems_index}")},
            translation_key="inverter",
            translation_placeholders={"inverter_num": str(ems_index + 1)},
            manufacturer=MANUFACTURER,
            model="Energy Management System",
            entry_type=DeviceEntryType.SERVICE,
            via_device=(DOMAIN, main_device_id),
        )

    def _get_sensor_device_info(self, main_device_id: str) -> DeviceInfo:
        """Return device info for a sensor device (grid, solar, load)."""
        if self.sensor_index is None:
            return self._get_system_device_info(main_device_id)

        if not self.coordinator.data or not self.coordinator.data.sensors:
            return self._get_fallback_sensor_device_info(main_device_id)

        sensor_index = self.sensor_index

        try:
            sensor_data = self.coordinator.data.sensors[sensor_index]
            sensor_type = sensor_data.type or "unknown"
            node_id = sensor_data.node_id
            euid = sensor_data.euid or "unknown"

            sensor_type_name = sensor_type.capitalize()

            # Map sensor type to translation key
            translation_key_map = {
                "grid": "grid",
                "solar": "solar",
                "load": "load",
            }
            device_translation_key = translation_key_map.get(sensor_type.lower())

            if device_translation_key:
                return DeviceInfo(
                    identifiers={(DOMAIN, f"sensor_{euid}")},
                    translation_key=device_translation_key,
                    manufacturer=MANUFACTURER,
                    model=f"{sensor_type_name} Sensor (Node {node_id})",
                    entry_type=DeviceEntryType.SERVICE,
                    via_device=(DOMAIN, main_device_id),
                )
            else:
                return DeviceInfo(
                    identifiers={(DOMAIN, f"sensor_{euid}")},
                    name=sensor_type_name,
                    manufacturer=MANUFACTURER,
                    model=f"{sensor_type_name} Sensor (Node {node_id})",
                    entry_type=DeviceEntryType.SERVICE,
                    via_device=(DOMAIN, main_device_id),
                )
        except IndexError:
            return self._get_fallback_sensor_device_info(main_device_id)

    def _get_fallback_sensor_device_info(self, main_device_id: str) -> DeviceInfo:
        """Return fallback device info for a sensor device."""
        sensor_index = self.sensor_index if self.sensor_index is not None else 0

        return DeviceInfo(
            identifiers={(DOMAIN, f"sensor_unknown_{sensor_index}")},
            name=f"Sensor {sensor_index + 1}",
            manufacturer=MANUFACTURER,
            model="Sensor",
            entry_type=DeviceEntryType.SERVICE,
            via_device=(DOMAIN, main_device_id),
        )

    def _get_system_device_info(self, main_device_id: str) -> DeviceInfo:
        """Return device info for the main system device."""
        return DeviceInfo(
            identifiers={(DOMAIN, main_device_id)},
            translation_key="system",
            manufacturer=MANUFACTURER,
            model="Energy Management System",
            entry_type=DeviceEntryType.SERVICE,
        )


class HomevoltBatteryEntity(HomevoltEntity):
    """Base class for Homevolt battery (BMS) entities."""

    def __init__(
        self,
        coordinator: HomevoltDataUpdateCoordinator,
        ems_index: int,
        bms_index: int,
    ) -> None:
        """Initialize the battery entity."""
        super().__init__(
            coordinator,
            ems_index=ems_index,
            sensor_index=None,
            bms_index=bms_index,
        )


class HomevoltInverterEntity(HomevoltEntity):
    """Base class for Homevolt inverter (EMS) entities."""

    def __init__(
        self,
        coordinator: HomevoltDataUpdateCoordinator,
        ems_index: int,
    ) -> None:
        """Initialize the inverter entity."""
        super().__init__(
            coordinator,
            ems_index=ems_index,
            sensor_index=None,
            bms_index=None,
        )


class HomevoltSensorDeviceEntity(HomevoltEntity):
    """Base class for Homevolt sensor device entities (grid, solar, load)."""

    def __init__(
        self,
        coordinator: HomevoltDataUpdateCoordinator,
        sensor_index: int,
    ) -> None:
        """Initialize the sensor device entity."""
        super().__init__(
            coordinator,
            ems_index=None,
            sensor_index=sensor_index,
            bms_index=None,
        )
