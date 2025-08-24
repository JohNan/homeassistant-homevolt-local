import unittest
from custom_components.homevolt_local.models import HomevoltData, EmsDevice, SensorData, EmsInfo, BmsInfo, InvInfo, EmsConfig, InvConfig, EmsControl, EmsData, BmsData, EmsPrediction, EmsVoltage, EmsCurrent, EmsAggregate, PhaseData, ScheduleEntry

class TestModels(unittest.TestCase):
    def test_homevolt_data_from_dict(self):
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
            "schedule_current_id": "test_id"
        }
        homevolt_data = HomevoltData.from_dict(data)
        self.assertEqual(homevolt_data.type, "homevolt.api.public.V1.SystemStatus, homevolt.api.public")
        self.assertEqual(homevolt_data.ts, 1672531200)
        self.assertEqual(len(homevolt_data.ems), 1)
        self.assertEqual(homevolt_data.ems[0].ecu_id, 123)
        self.assertEqual(homevolt_data.aggregated.ecu_id, 456)
        self.assertEqual(len(homevolt_data.sensors), 1)
        self.assertEqual(homevolt_data.sensors[0].type, "grid")
        self.assertEqual(len(homevolt_data.schedules), 1)
        self.assertEqual(homevolt_data.schedules[0]['type'], "charge")
        self.assertEqual(homevolt_data.schedule_count, 1)
        self.assertEqual(homevolt_data.schedule_current_id, "test_id")

    def test_ems_device_from_dict_empty(self):
        """Test creating an EmsDevice object from an empty dictionary."""
        ems_device = EmsDevice.from_dict({})
        self.assertIsInstance(ems_device, EmsDevice)
        self.assertEqual(ems_device.ecu_id, 0)

    def test_sensor_data_from_dict(self):
        """Test creating a SensorData object from a dictionary."""
        data = {
            "type": "solar",
            "node_id": 2,
            "euid": "sensor2",
            "phase": [
                {"voltage": 230.0, "amp": 5.0, "power": 1150.0, "pf": 1.0}
            ],
            "total_power": 1150
        }
        sensor_data = SensorData.from_dict(data)
        self.assertEqual(sensor_data.type, "solar")
        self.assertEqual(sensor_data.node_id, 2)
        self.assertEqual(sensor_data.euid, "sensor2")
        self.assertEqual(len(sensor_data.phase), 1)
        self.assertEqual(sensor_data.phase[0].voltage, 230.0)
        self.assertEqual(sensor_data.total_power, 1150)

    def test_schedule_entry_model(self):
        """Test the ScheduleEntry model."""
        schedule = ScheduleEntry(
            id=1,
            type="charge",
            from_time="2023-01-01T00:00:00",
            to_time="2023-01-01T01:00:00",
            setpoint=1000,
            offline=False,
            max_charge="<max allowed>"
        )
        self.assertEqual(schedule.id, 1)
        self.assertEqual(schedule.type, "charge")
        self.assertEqual(schedule.from_time, "2023-01-01T00:00:00")
        self.assertEqual(schedule.to_time, "2023-01-01T01:00:00")
        self.assertEqual(schedule.setpoint, 1000)
        self.assertFalse(schedule.offline)
        self.assertEqual(schedule.max_charge, "<max allowed>")

if __name__ == '__main__':
    unittest.main()
