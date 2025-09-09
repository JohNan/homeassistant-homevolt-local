import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, PropertyMock, patch, AsyncMock
import asyncio

from custom_components.homevolt_local.models import HomevoltData, ScheduleEntry
from custom_components.homevolt_local.sensor import get_current_schedule, HomevoltSensor, HomevoltSensorEntityDescription, async_setup_entry
from custom_components.homevolt_local.const import DOMAIN
from .test_utils import mock_homevolt_data
from pytest_homeassistant_custom_component.common import MockConfigEntry

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
        mock_coordinator.data = mock_homevolt_data(num_ems=1, num_sensors=1)

        # Aggregated sensor
        description = HomevoltSensorEntityDescription(key="power", name="Power")
        sensor = HomevoltSensor(mock_coordinator, description)
        self.assertEqual(sensor.unique_id, "homevolt_local_power_192.168.1.1")

        # Device-specific sensor
        description = HomevoltSensorEntityDescription(key="ems_1_power", name="EMS 1 Power", device_specific=True)
        sensor = HomevoltSensor(mock_coordinator, description, ems_index=0)
        self.assertEqual(sensor.unique_id, "homevolt_local_ems_1_power_ems_ecu_0")

        # Sensor-specific sensor
        description = HomevoltSensorEntityDescription(key="grid_power", name="Grid Power", sensor_specific=True)
        sensor = HomevoltSensor(mock_coordinator, description, sensor_index=0)
        self.assertEqual(sensor.unique_id, "homevolt_local_grid_power_sensor_sensor_0")

    def test_device_specific_sensor_entity_ids_unittest(self):
        """Test the entity IDs for device-specific sensors using unittest style."""

        async def run_test():
            hass = MagicMock()
            hass.data = {DOMAIN: {}}

            # Create a mock config entry
            config_entry = MockConfigEntry(domain=DOMAIN, data={}, entry_id="test")

            # Create a mock coordinator with two EMS devices
            mock_coordinator = MagicMock()
            mock_coordinator.data = mock_homevolt_data(num_ems=2)
            mock_coordinator.resource = "http://192.168.1.1/api/v1/data"

            hass.data[DOMAIN] = {config_entry.entry_id: mock_coordinator}

            async_add_entities = MagicMock()

            # Setup the sensor platform
            await async_setup_entry(hass, config_entry, async_add_entities)

            # Check that the entity IDs are correct
            added_sensors = async_add_entities.call_args[0][0]

            entity_ids = [sensor.entity_description.key for sensor in added_sensors if sensor.ems_index is not None]
            names = [sensor.name for sensor in added_sensors if sensor.ems_index is not None]

            # Expected keys
            self.assertIn("ems_1_status", entity_ids)
            self.assertIn("ems_2_status", entity_ids)

            # Expected names
            self.assertIn("EMS 1 Status", names)
            self.assertIn("EMS 2 Status", names)

        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()
