import unittest
from custom_components.homevolt_local import HomevoltDataUpdateCoordinator

class TestCoordinator(unittest.TestCase):
    def test_merge_data(self):
        """Test the merging of data from multiple systems."""
        # We don't need a real coordinator object, just something to call the method on
        coordinator = HomevoltDataUpdateCoordinator(None, None, None, [], [], "", None, None, None, None, None)

        main_data = {
            "aggregated": {"ecu_id": 1},
            "ems": [{"ecu_id": 1, "data": "main_ems_1"}],
            "sensors": [{"euid": "sensor1", "data": "main_sensor_1"}]
        }

        results = [
            ("host1", {
                "ems": [{"ecu_id": 1, "data": "host1_ems_1"}, {"ecu_id": 2, "data": "host1_ems_2"}],
                "sensors": [{"euid": "sensor1", "data": "host1_sensor_1"}]
            }),
            ("host2", {
                "ems": [{"ecu_id": 3, "data": "host2_ems_3"}],
                "sensors": [{"euid": "sensor2", "data": "host2_sensor_2"}, {"euid": "sensor3", "data": "host2_sensor_3"}]
            })
        ]

        merged_data = coordinator._merge_data(results, main_data)

        # The aggregated data should be from the main data
        self.assertEqual(merged_data["aggregated"]["ecu_id"], 1)

        # The ems list should contain unique devices from all results
        self.assertEqual(len(merged_data["ems"]), 3)
        self.assertIn({"ecu_id": 1, "data": "main_ems_1"}, merged_data["ems"])
        self.assertIn({"ecu_id": 2, "data": "host1_ems_2"}, merged_data["ems"])
        self.assertIn({"ecu_id": 3, "data": "host2_ems_3"}, merged_data["ems"])

        # The sensors list should contain unique sensors from all results
        self.assertEqual(len(merged_data["sensors"]), 3)
        self.assertIn({"euid": "sensor1", "data": "main_sensor_1"}, merged_data["sensors"])
        self.assertIn({"euid": "sensor2", "data": "host2_sensor_2"}, merged_data["sensors"])
        self.assertIn({"euid": "sensor3", "data": "host2_sensor_3"}, merged_data["sensors"])

if __name__ == '__main__':
    unittest.main()
