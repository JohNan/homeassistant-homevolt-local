"""Tests for Homevolt Local entity base classes."""

from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.helpers.device_registry import DeviceEntryType

from custom_components.homevolt_local.const import DOMAIN
from custom_components.homevolt_local.entity import (
    MANUFACTURER,
    HomevoltBatteryEntity,
    HomevoltEntity,
    HomevoltInverterEntity,
    HomevoltSensorDeviceEntity,
)
from custom_components.homevolt_local.models import HomevoltData


def create_mock_coordinator(
    data: HomevoltData | None = None,
    main_device_id: str = "test_device_123",
) -> MagicMock:
    """Create a mock coordinator with optional data."""
    coordinator = MagicMock()
    coordinator.data = data
    coordinator.get_main_device_id.return_value = main_device_id
    return coordinator


def create_test_homevolt_data(
    ems_count: int = 1,
    bms_per_ems: int = 1,
    sensor_count: int = 1,
) -> HomevoltData:
    """Create test HomevoltData with configurable device counts."""
    ems_list = []
    for i in range(ems_count):
        bms_data_list = [
            {"soc": 5000, "tmax": 25.0, "tmin": 20.0} for _ in range(bms_per_ems)
        ]
        bms_info_list = [
            {
                "fw_version": f"2.{j}.0",
                "serial_number": f"BMS{i:02d}{j:02d}",
                "rated_cap": 5000,
                "id": j,
            }
            for j in range(bms_per_ems)
        ]
        ems_list.append(
            {
                "ecu_id": f"ecu_{i:03d}",
                "ems_data": {
                    "state_str": "idle",
                    "soc_avg": 50.0,
                    "power": 100.0,
                    "energy_produced": 1000.0,
                    "energy_consumed": 500.0,
                },
                "error_str": "",
                "inv_info": {"serial_number": f"INV{i:03d}"},
                "ems_info": {"fw_version": f"1.{i}.0", "rated_capacity": 10000},
                "bms_data": bms_data_list,
                "bms_info": bms_info_list,
            }
        )

    sensors = []
    sensor_types = ["grid", "solar", "load"]
    for i in range(sensor_count):
        sensor_type = sensor_types[i % len(sensor_types)]
        sensors.append(
            {
                "euid": f"sensor_{i:03d}",
                "type": sensor_type,
                "total_power": 200.0,
                "energy_imported": 2000.0,
                "energy_exported": 1000.0,
                "available": True,
                "node_id": i,
            }
        )

    return HomevoltData.from_dict(
        {
            "aggregated": {
                "ems_data": {
                    "state_str": "idle",
                    "soc_avg": 50.0,
                    "power": 100.0,
                    "energy_produced": 1000.0,
                    "energy_consumed": 500.0,
                },
                "error_str": "",
                "bms_data": [{"soc": 5000, "tmax": 25.0, "tmin": 20.0}],
            },
            "ems": ems_list,
            "sensors": sensors,
        }
    )


class TestHomevoltEntity:
    """Tests for the HomevoltEntity base class."""

    def test_init_default_indices(self) -> None:
        """Test entity initialization with default indices."""
        coordinator = create_mock_coordinator()
        entity = HomevoltEntity(coordinator)

        assert entity.ems_index is None
        assert entity.sensor_index is None
        assert entity.bms_index is None
        assert entity.coordinator is coordinator

    def test_init_with_indices(self) -> None:
        """Test entity initialization with specific indices."""
        coordinator = create_mock_coordinator()
        entity = HomevoltEntity(coordinator, ems_index=1, sensor_index=2, bms_index=3)

        assert entity.ems_index == 1
        assert entity.sensor_index == 2
        assert entity.bms_index == 3

    def test_main_device_id(self) -> None:
        """Test main_device_id property."""
        coordinator = create_mock_coordinator(main_device_id="my_device")
        entity = HomevoltEntity(coordinator)

        assert entity.main_device_id == "homevolt_my_device"

    def test_data_property(self) -> None:
        """Test data property returns coordinator data."""
        data = create_test_homevolt_data()
        coordinator = create_mock_coordinator(data=data)
        entity = HomevoltEntity(coordinator)

        assert entity.data is data

    def test_data_property_none(self) -> None:
        """Test data property when coordinator has no data."""
        coordinator = create_mock_coordinator(data=None)
        entity = HomevoltEntity(coordinator)

        assert entity.data is None

    def test_has_entity_name_attribute(self) -> None:
        """Test entity has _attr_has_entity_name set."""
        coordinator = create_mock_coordinator()
        entity = HomevoltEntity(coordinator)

        assert entity._attr_has_entity_name is True


class TestHomevoltEntityDeviceInfo:
    """Tests for HomevoltEntity device_info property."""

    def test_system_device_info(self) -> None:
        """Test device info for system-level entity (no indices)."""
        coordinator = create_mock_coordinator(main_device_id="test_123")
        entity = HomevoltEntity(coordinator)

        device_info = entity.device_info

        assert device_info.get("identifiers") == {(DOMAIN, "homevolt_test_123")}
        assert device_info.get("translation_key") == "system"
        assert device_info.get("manufacturer") == MANUFACTURER
        assert device_info.get("model") == "Energy Management System"
        assert device_info.get("entry_type") == DeviceEntryType.SERVICE

    def test_ems_device_info_with_data(self) -> None:
        """Test device info for EMS entity with coordinator data."""
        data = create_test_homevolt_data(ems_count=1)
        coordinator = create_mock_coordinator(data=data, main_device_id="test_123")
        entity = HomevoltEntity(coordinator, ems_index=0)

        device_info = entity.device_info

        assert device_info.get("identifiers") == {(DOMAIN, "ems_ecu_000")}
        assert device_info.get("translation_key") == "inverter"
        assert device_info.get("translation_placeholders") == {"inverter_num": "1"}
        assert device_info.get("manufacturer") == MANUFACTURER
        model = device_info.get("model")
        assert model is not None and "1.0.0" in model
        assert device_info.get("via_device") == (DOMAIN, "homevolt_test_123")
        assert device_info.get("sw_version") == "1.0.0"
        assert device_info.get("hw_version") == "INV000"

    def test_ems_device_info_fallback_no_data(self) -> None:
        """Test EMS device info falls back when no coordinator data."""
        coordinator = create_mock_coordinator(data=None, main_device_id="test_123")
        entity = HomevoltEntity(coordinator, ems_index=0)

        device_info = entity.device_info

        assert device_info.get("identifiers") == {(DOMAIN, "ems_unknown_0")}
        assert device_info.get("translation_key") == "inverter"
        assert device_info.get("translation_placeholders") == {"inverter_num": "1"}
        assert device_info.get("via_device") == (DOMAIN, "homevolt_test_123")

    def test_ems_device_info_index_out_of_range(self) -> None:
        """Test EMS device info with out-of-range index falls back."""
        data = create_test_homevolt_data(ems_count=1)
        coordinator = create_mock_coordinator(data=data, main_device_id="test_123")
        entity = HomevoltEntity(coordinator, ems_index=5)  # Out of range

        device_info = entity.device_info

        # Should use fallback
        assert device_info.get("identifiers") == {(DOMAIN, "ems_unknown_5")}

    def test_bms_device_info_with_data(self) -> None:
        """Test device info for BMS entity with coordinator data."""
        data = create_test_homevolt_data(ems_count=1, bms_per_ems=2)
        coordinator = create_mock_coordinator(data=data, main_device_id="test_123")
        entity = HomevoltEntity(coordinator, ems_index=0, bms_index=1)

        device_info = entity.device_info

        # BMS serial is BMS0001 (ems_index=0, bms_index=1)
        assert device_info.get("identifiers") == {(DOMAIN, "bms_ecu_000_BMS0001")}
        assert device_info.get("translation_key") == "battery"
        assert device_info.get("translation_placeholders") == {
            "inverter_num": "1",
            "battery_num": "2",  # bms_index 1 has id=1, so bms_id = 2
        }
        assert device_info.get("manufacturer") == MANUFACTURER
        assert device_info.get("model") == "Battery Module"
        assert device_info.get("via_device") == (DOMAIN, "ems_ecu_000")
        assert device_info.get("sw_version") == "2.1.0"
        assert device_info.get("hw_version") == "BMS0001"

    def test_bms_device_info_fallback_no_data(self) -> None:
        """Test BMS device info falls back when no coordinator data."""
        coordinator = create_mock_coordinator(data=None, main_device_id="test_123")
        entity = HomevoltEntity(coordinator, ems_index=0, bms_index=1)

        device_info = entity.device_info

        assert device_info.get("identifiers") == {(DOMAIN, "bms_unknown_0_1")}
        assert device_info.get("translation_key") == "battery"
        assert device_info.get("translation_placeholders") == {
            "inverter_num": "1",
            "battery_num": "2",
        }
        assert device_info.get("via_device") == (DOMAIN, "homevolt_test_123")

    def test_bms_device_info_bms_index_out_of_range(self) -> None:
        """Test BMS device info with out-of-range bms_index falls back."""
        data = create_test_homevolt_data(ems_count=1, bms_per_ems=1)
        coordinator = create_mock_coordinator(data=data, main_device_id="test_123")
        entity = HomevoltEntity(coordinator, ems_index=0, bms_index=5)  # Out of range

        device_info = entity.device_info

        # Should still work but bms_info won't be available
        assert "bms_" in str(device_info.get("identifiers"))

    def test_sensor_device_info_grid(self) -> None:
        """Test device info for grid sensor."""
        data = create_test_homevolt_data(sensor_count=1)  # Creates grid sensor
        coordinator = create_mock_coordinator(data=data, main_device_id="test_123")
        entity = HomevoltEntity(coordinator, sensor_index=0)

        device_info = entity.device_info

        assert device_info.get("identifiers") == {(DOMAIN, "sensor_sensor_000")}
        assert device_info.get("translation_key") == "grid"
        assert device_info.get("manufacturer") == MANUFACTURER
        model = device_info.get("model")
        assert model is not None and "Grid" in model
        assert device_info.get("via_device") == (DOMAIN, "homevolt_test_123")

    def test_sensor_device_info_solar(self) -> None:
        """Test device info for solar sensor."""
        data = create_test_homevolt_data(sensor_count=2)  # Creates grid, solar
        coordinator = create_mock_coordinator(data=data, main_device_id="test_123")
        entity = HomevoltEntity(coordinator, sensor_index=1)

        device_info = entity.device_info

        assert device_info.get("identifiers") == {(DOMAIN, "sensor_sensor_001")}
        assert device_info.get("translation_key") == "solar"
        model = device_info.get("model")
        assert model is not None and "Solar" in model

    def test_sensor_device_info_load(self) -> None:
        """Test device info for load sensor."""
        data = create_test_homevolt_data(sensor_count=3)  # Creates grid, solar, load
        coordinator = create_mock_coordinator(data=data, main_device_id="test_123")
        entity = HomevoltEntity(coordinator, sensor_index=2)

        device_info = entity.device_info

        assert device_info.get("identifiers") == {(DOMAIN, "sensor_sensor_002")}
        assert device_info.get("translation_key") == "load"
        model = device_info.get("model")
        assert model is not None and "Load" in model

    def test_sensor_device_info_fallback_no_data(self) -> None:
        """Test sensor device info falls back when no coordinator data."""
        coordinator = create_mock_coordinator(data=None, main_device_id="test_123")
        entity = HomevoltEntity(coordinator, sensor_index=0)

        device_info = entity.device_info

        assert device_info.get("identifiers") == {(DOMAIN, "sensor_unknown_0")}
        assert device_info.get("name") == "Sensor 1"
        assert device_info.get("model") == "Sensor"
        assert device_info.get("via_device") == (DOMAIN, "homevolt_test_123")

    def test_sensor_device_info_unknown_type(self) -> None:
        """Test sensor device info for unknown sensor type."""
        # Manually create data with unknown sensor type
        data = HomevoltData.from_dict(
            {
                "aggregated": {
                    "ems_data": {
                        "state_str": "idle",
                        "soc_avg": 50.0,
                        "power": 100.0,
                    },
                    "error_str": "",
                    "bms_data": [],
                },
                "ems": [],
                "sensors": [
                    {
                        "euid": "sensor_unknown",
                        "type": "custom_type",
                        "total_power": 100.0,
                        "available": True,
                        "node_id": 0,
                    }
                ],
            }
        )
        coordinator = create_mock_coordinator(data=data, main_device_id="test_123")
        entity = HomevoltEntity(coordinator, sensor_index=0)

        device_info = entity.device_info

        # Should use name instead of translation_key
        assert device_info.get("identifiers") == {(DOMAIN, "sensor_sensor_unknown")}
        assert device_info.get("name") == "Custom_type"
        assert device_info.get("translation_key") is None


class TestHomevoltBatteryEntity:
    """Tests for HomevoltBatteryEntity subclass."""

    def test_init(self) -> None:
        """Test battery entity initialization."""
        coordinator = create_mock_coordinator()
        entity = HomevoltBatteryEntity(coordinator, ems_index=1, bms_index=2)

        assert entity.ems_index == 1
        assert entity.bms_index == 2
        assert entity.sensor_index is None

    def test_device_info_returns_bms_info(self) -> None:
        """Test battery entity returns BMS device info."""
        data = create_test_homevolt_data(ems_count=2, bms_per_ems=3)
        coordinator = create_mock_coordinator(data=data, main_device_id="test_123")
        entity = HomevoltBatteryEntity(coordinator, ems_index=1, bms_index=2)

        device_info = entity.device_info

        # BMS serial is BMS0102 (ems_index=1, bms_index=2)
        assert "bms_ecu_001" in str(device_info.get("identifiers"))
        assert device_info.get("translation_key") == "battery"


class TestHomevoltInverterEntity:
    """Tests for HomevoltInverterEntity subclass."""

    def test_init(self) -> None:
        """Test inverter entity initialization."""
        coordinator = create_mock_coordinator()
        entity = HomevoltInverterEntity(coordinator, ems_index=2)

        assert entity.ems_index == 2
        assert entity.bms_index is None
        assert entity.sensor_index is None

    def test_device_info_returns_ems_info(self) -> None:
        """Test inverter entity returns EMS device info."""
        data = create_test_homevolt_data(ems_count=3)
        coordinator = create_mock_coordinator(data=data, main_device_id="test_123")
        entity = HomevoltInverterEntity(coordinator, ems_index=1)

        device_info = entity.device_info

        assert device_info.get("identifiers") == {(DOMAIN, "ems_ecu_001")}
        assert device_info.get("translation_key") == "inverter"
        assert device_info.get("translation_placeholders") == {"inverter_num": "2"}


class TestHomevoltSensorDeviceEntity:
    """Tests for HomevoltSensorDeviceEntity subclass."""

    def test_init(self) -> None:
        """Test sensor device entity initialization."""
        coordinator = create_mock_coordinator()
        entity = HomevoltSensorDeviceEntity(coordinator, sensor_index=3)

        assert entity.sensor_index == 3
        assert entity.ems_index is None
        assert entity.bms_index is None

    def test_device_info_returns_sensor_info(self) -> None:
        """Test sensor device entity returns sensor device info."""
        data = create_test_homevolt_data(sensor_count=4)
        coordinator = create_mock_coordinator(data=data, main_device_id="test_123")
        entity = HomevoltSensorDeviceEntity(coordinator, sensor_index=1)

        device_info = entity.device_info

        assert device_info.get("identifiers") == {(DOMAIN, "sensor_sensor_001")}
        # sensor_index=1 is solar type
        assert device_info.get("translation_key") == "solar"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_ems_list(self) -> None:
        """Test handling of empty EMS list."""
        data = HomevoltData.from_dict(
            {
                "aggregated": {
                    "ems_data": {"state_str": "idle", "power": 0},
                    "error_str": "",
                    "bms_data": [],
                },
                "ems": [],
                "sensors": [],
            }
        )
        coordinator = create_mock_coordinator(data=data, main_device_id="test_123")
        entity = HomevoltEntity(coordinator, ems_index=0)

        # Should return fallback
        device_info = entity.device_info
        assert device_info.get("identifiers") == {(DOMAIN, "ems_unknown_0")}

    def test_empty_sensors_list(self) -> None:
        """Test handling of empty sensors list."""
        data = HomevoltData.from_dict(
            {
                "aggregated": {
                    "ems_data": {"state_str": "idle", "power": 0},
                    "error_str": "",
                    "bms_data": [],
                },
                "ems": [],
                "sensors": [],
            }
        )
        coordinator = create_mock_coordinator(data=data, main_device_id="test_123")
        entity = HomevoltEntity(coordinator, sensor_index=0)

        # Should return fallback
        device_info = entity.device_info
        assert device_info.get("identifiers") == {(DOMAIN, "sensor_unknown_0")}

    def test_ems_with_no_bms_info(self) -> None:
        """Test EMS device with missing BMS info."""
        data = HomevoltData.from_dict(
            {
                "aggregated": {
                    "ems_data": {"state_str": "idle", "power": 0},
                    "error_str": "",
                    "bms_data": [],
                },
                "ems": [
                    {
                        "ecu_id": "ecu_test",
                        "ems_data": {"state_str": "idle", "power": 0},
                        "error_str": "",
                        "bms_data": [],
                        "bms_info": [],  # Empty
                    }
                ],
                "sensors": [],
            }
        )
        coordinator = create_mock_coordinator(data=data, main_device_id="test_123")
        entity = HomevoltEntity(coordinator, ems_index=0, bms_index=0)

        device_info = entity.device_info

        # Should handle gracefully with fallback bms serial
        assert "bms_ecu_test" in str(device_info.get("identifiers"))

    def test_ems_with_missing_ecu_id(self) -> None:
        """Test EMS device with missing ECU ID."""
        data = HomevoltData.from_dict(
            {
                "aggregated": {
                    "ems_data": {"state_str": "idle", "power": 0},
                    "error_str": "",
                    "bms_data": [],
                },
                "ems": [
                    {
                        "ecu_id": None,  # Missing
                        "ems_data": {"state_str": "idle", "power": 0},
                        "error_str": "",
                    }
                ],
                "sensors": [],
            }
        )
        coordinator = create_mock_coordinator(data=data, main_device_id="test_123")
        entity = HomevoltEntity(coordinator, ems_index=0)

        device_info = entity.device_info

        # Should use fallback ecu_id
        assert device_info.get("identifiers") == {(DOMAIN, "ems_unknown_0")}

    def test_sensor_with_missing_euid(self) -> None:
        """Test sensor with missing EUID."""
        data = HomevoltData.from_dict(
            {
                "aggregated": {
                    "ems_data": {"state_str": "idle", "power": 0},
                    "error_str": "",
                    "bms_data": [],
                },
                "ems": [],
                "sensors": [
                    {
                        "euid": None,  # Missing
                        "type": "grid",
                        "total_power": 100.0,
                        "node_id": 0,
                    }
                ],
            }
        )
        coordinator = create_mock_coordinator(data=data, main_device_id="test_123")
        entity = HomevoltEntity(coordinator, sensor_index=0)

        device_info = entity.device_info

        # Should use "unknown" as euid
        assert device_info.get("identifiers") == {(DOMAIN, "sensor_unknown")}
