"""Tests for Homevolt Local models."""

from __future__ import annotations

from custom_components.homevolt_local.models import (
    EmsDevice,
    HomevoltData,
    ScheduleEntry,
    SensorData,
)


class TestHomevoltData:
    """Tests for HomevoltData model."""

    def test_from_dict(self) -> None:
        """Test creating a HomevoltData object from a dictionary."""
        data = {
            "$type": "homevolt.api.public.V1.SystemStatus, homevolt.api.public",
            "ts": 1672531200,
            "ems": [
                {
                    "ecu_id": 123,
                }
            ],
            "aggregated": {
                "ecu_id": 456,
            },
            "sensors": [
                {
                    "type": "grid",
                    "node_id": 1,
                    "euid": "sensor1",
                }
            ],
            "schedules": [
                {
                    "id": 1,
                    "type": "charge",
                    "from": "2023-01-01T00:00:00",
                    "to": "2023-01-01T01:00:00",
                }
            ],
            "schedule_count": 1,
            "schedule_current_id": "test_id",
        }
        homevolt_data = HomevoltData.from_dict(data)

        assert (
            homevolt_data.type
            == "homevolt.api.public.V1.SystemStatus, homevolt.api.public"
        )
        assert homevolt_data.ts == 1672531200
        assert len(homevolt_data.ems) == 1
        assert homevolt_data.ems[0].ecu_id == 123
        assert homevolt_data.aggregated.ecu_id == 456
        assert len(homevolt_data.sensors) == 1
        assert homevolt_data.sensors[0].type == "grid"
        assert len(homevolt_data.schedules) == 1
        # Note: schedules are stored as raw dicts from the API
        assert homevolt_data.schedules[0]["type"] == "charge"  # type: ignore[index]
        assert homevolt_data.schedule_count == 1
        assert homevolt_data.schedule_current_id == "test_id"


class TestEmsDevice:
    """Tests for EmsDevice model."""

    def test_from_dict_empty(self) -> None:
        """Test creating an EmsDevice object from an empty dictionary."""
        ems_device = EmsDevice.from_dict({})

        assert isinstance(ems_device, EmsDevice)
        assert ems_device.ecu_id == 0


class TestSensorData:
    """Tests for SensorData model."""

    def test_from_dict(self) -> None:
        """Test creating a SensorData object from a dictionary."""
        data = {
            "type": "solar",
            "node_id": 2,
            "euid": "sensor2",
            "phase": [{"voltage": 230.0, "amp": 5.0, "power": 1150.0, "pf": 1.0}],
            "total_power": 1150,
        }
        sensor_data = SensorData.from_dict(data)

        assert sensor_data.type == "solar"
        assert sensor_data.node_id == 2
        assert sensor_data.euid == "sensor2"
        assert len(sensor_data.phase) == 1
        assert sensor_data.phase[0].voltage == 230.0
        assert sensor_data.total_power == 1150


class TestScheduleEntry:
    """Tests for ScheduleEntry model."""

    def test_schedule_entry_model(self) -> None:
        """Test the ScheduleEntry model."""
        schedule = ScheduleEntry(
            id=1,
            type="charge",
            from_time="2023-01-01T00:00:00",
            to_time="2023-01-01T01:00:00",
            setpoint=1000,
            offline=False,
            max_charge="<max allowed>",
        )

        assert schedule.id == 1
        assert schedule.type == "charge"
        assert schedule.from_time == "2023-01-01T00:00:00"
        assert schedule.to_time == "2023-01-01T01:00:00"
        assert schedule.setpoint == 1000
        assert schedule.offline is False
        assert schedule.max_charge == "<max allowed>"
