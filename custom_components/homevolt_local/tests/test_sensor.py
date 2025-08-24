import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, PropertyMock

from custom_components.homevolt_local.models import HomevoltData, ScheduleEntry
from custom_components.homevolt_local.sensor import get_current_schedule, HomevoltSensor, HomevoltSensorEntityDescription

class TestSensor(unittest.TestCase):
    def test_get_current_schedule(self):
        """Test the get_current_schedule function."""
        now = datetime.now()
        schedules = [
            ScheduleEntry(id=1, type="charge", from_time=(now - timedelta(hours=1)).isoformat(), to_time=(now + timedelta(hours=1)).isoformat()),
            ScheduleEntry(id=2, type="discharge", from_time=(now + timedelta(hours=2)).isoformat(), to_time=(now + timedelta(hours=3)).isoformat()),
        ]
        data = HomevoltData.from_dict({"schedules": [s.__dict__ for s in schedules]})

        # The from_dict method doesn't handle the ScheduleEntry objects, so we set them manually
        data.schedules = schedules

        self.assertEqual(get_current_schedule(data), "charge")

        schedules = [
            ScheduleEntry(id=1, type="charge", from_time=(now - timedelta(hours=2)).isoformat(), to_time=(now - timedelta(hours=1)).isoformat()),
            ScheduleEntry(id=2, type="discharge", from_time=(now + timedelta(hours=2)).isoformat(), to_time=(now + timedelta(hours=3)).isoformat()),
        ]
        data.schedules = schedules
        self.assertEqual(get_current_schedule(data), "No active schedule")

    def test_homevolt_sensor_unique_id(self):
        """Test the unique_id generation for HomevoltSensor."""
        mock_coordinator = MagicMock()
        type(mock_coordinator).resource = PropertyMock(return_value="https://192.168.1.1/api/v1/data")

        # Aggregated sensor
        description = HomevoltSensorEntityDescription(key="power", name="Power")
        sensor = HomevoltSensor(mock_coordinator, description)
        self.assertEqual(sensor.unique_id, "homevolt_local_power_192.168.1.1")

        # Device-specific sensor
        mock_coordinator.data = HomevoltData.from_dict({
            "ems": [{"ecu_id": 12345}]
        })
        description = HomevoltSensorEntityDescription(key="device_power", name="Device Power", device_specific=True)
        sensor = HomevoltSensor(mock_coordinator, description, ems_index=0)
        self.assertEqual(sensor.unique_id, "homevolt_local_device_power_ems_12345")

        # Sensor-specific sensor
        mock_coordinator.data = HomevoltData.from_dict({
            "sensors": [{"euid": "abcdef"}]
        })
        description = HomevoltSensorEntityDescription(key="grid_power", name="Grid Power", sensor_specific=True)
        sensor = HomevoltSensor(mock_coordinator, description, sensor_index=0)
        self.assertEqual(sensor.unique_id, "homevolt_local_grid_power_sensor_abcdef")

if __name__ == '__main__':
    unittest.main()
