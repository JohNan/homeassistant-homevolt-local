import unittest
from custom_components.homevolt_local import HomevoltDataUpdateCoordinator
from custom_components.homevolt_local.models import ScheduleEntry


class TestHomevoltDataUpdateCoordinator(unittest.TestCase):
    def test_parse_schedule_data(self):
        """Test parsing of schedule data."""
        coordinator = HomevoltDataUpdateCoordinator(
            hass=None,
            logger=None,
            entry_id=None,
            resources=[],
            hosts=[],
            main_host="",
            username="",
            password="",
            session=None,
            update_interval=None,
            timeout=None,
        )

        test_string = """
esp32> sched_list
Schedule get: 27 schedules. Current ID: 'linear-optimization2-2025-08-23 21:09'
id: 0, type: Idle schedule, from: 2025-08-23T23:00:00, to: 2025-08-23T23:30:00, offline: false
id: 1, type: Grid discharge setpoint, from: 2025-08-23T23:30:00, to: 2025-08-24T00:00:00, setpoint:0, max_discharge: <max allowed>
id: 2, type: Idle schedule, from: 2025-08-24T00:00:00, to: 2025-08-24T10:00:00, offline: false
id: 3, type: Grid charge setpoint, from: 2025-08-24T10:00:00, to: 2025-08-24T10:45:00, setpoint:0, max_charge: <max allowed>
id: 4, type: Inverter charge setpoint, from: 2025-08-24T10:45:00, to: 2025-08-24T11:00:00, setpoint: 1958
id: 5, type: Grid charge setpoint, from: 2025-08-24T11:00:00, to: 2025-08-24T11:30:00, setpoint:0, max_charge: <max allowed>
id: 6, type: Inverter charge setpoint, from: 2025-08-24T11:30:00, to: 2025-08-24T11:45:00, setpoint: 1849
id: 7, type: Inverter charge setpoint, from: 2025-08-24T11:45:00, to: 2025-08-24T12:00:00, setpoint: 2698
id: 8, type: Grid charge setpoint, from: 2025-08-24T12:00:00, to: 2025-08-24T14:00:00, setpoint:0, max_charge: <max allowed>
id: 9, type: Inverter charge setpoint, from: 2025-08-24T14:00:00, to: 2025-08-24T14:15:00, setpoint: 4939
id: 10, type: Grid charge setpoint, from: 2025-08-24T14:15:00, to: 2025-08-24T14:30:00, setpoint:0, max_charge: <max allowed>
id: 11, type: Inverter charge setpoint, from: 2025-08-24T14:30:00, to: 2025-08-24T14:45:00, setpoint: 3675
id: 12, type: Inverter charge setpoint, from: 2025-08-24T14:45:00, to: 2025-08-24T15:00:00, setpoint: 4970
id: 13, type: Inverter charge setpoint, from: 2025-08-24T15:00:00, to: 2025-08-24T15:15:00, setpoint: 4834
id: 14, type: Inverter charge setpoint, from: 2025-08-24T15:15:00, to: 2025-08-24T15:30:00, setpoint: 4420
id: 15, type: Inverter charge setpoint, from: 2025-08-24T15:30:00, to: 2025-08-24T15:45:00, setpoint: 4344
id: 16, type: Inverter charge setpoint, from: 2025-08-24T15:45:00, to: 2025-08-24T16:00:00, setpoint: 4401
id: 17, type: Grid charge setpoint, from: 2025-08-24T16:00:00, to: 2025-08-24T16:30:00, setpoint:0, max_charge: <max allowed>
id: 18, type: Inverter charge setpoint, from: 2025-08-24T16:30:00, to: 2025-08-24T16:45:00, setpoint: 2688
id: 19, type: Inverter charge setpoint, from: 2025-08-24T16:45:00, to: 2025-08-24T17:00:00, setpoint: 738
id: 20, type: Idle schedule, from: 2025-08-24T17:00:00, to: 2025-08-24T18:30:00, offline: false
id: 21, type: Grid discharge setpoint, from: 2025-08-24T18:30:00, to: 2025-08-24T18:45:00, setpoint:0, max_discharge: <max allowed>
id: 22, type: Idle schedule, from: 2025-08-24T18:45:00, to: 2025-08-24T19:00:00, offline: false
id: 23, type: Inverter discharge setpoint, from: 2025-08-24T19:00:00, to: 2025-08-24T20:45:00, setpoint: 12056
id: 24, type: Inverter discharge setpoint, from: 2025-08-24T20:45:00, to: 2025-08-24T21:00:00, setpoint: 7601
id: 25, type: Grid discharge setpoint, from: 2025-08-24T21:00:00, to: 2025-08-24T22:00:00, setpoint:0, max_discharge: <max allowed>
id: 26, type: Idle schedule, from: 2025-08-24T22:00:00, to: 2025-08-25T00:00:00, offline: false
Command 'sched_list' executed successfully
"""
        schedules = coordinator._parse_schedule_data(test_string)

        self.assertEqual(len(schedules), 27)

        self.assertEqual(schedules[0], ScheduleEntry(
            id=0, type='Idle schedule', from_time='2025-08-23T23:00:00',
            to_time='2025-08-23T23:30:00', setpoint=None, offline=False,
            max_discharge=None, max_charge=None
        ))
        self.assertEqual(schedules[1], ScheduleEntry(
            id=1, type='Grid discharge setpoint', from_time='2025-08-23T23:30:00',
            to_time='2025-08-24T00:00:00', setpoint=0, offline=None,
            max_discharge='<max allowed>', max_charge=None
        ))
        self.assertEqual(schedules[23], ScheduleEntry(
            id=23, type='Inverter discharge setpoint', from_time='2025-08-24T19:00:00',
            to_time='2025-08-24T20:45:00', setpoint=12056, offline=None,
            max_discharge=None, max_charge=None
        ))
        self.assertEqual(schedules[26], ScheduleEntry(
            id=26, type='Idle schedule', from_time='2025-08-24T22:00:00',
            to_time='2025-08-25T00:00:00', setpoint=None, offline=False,
            max_discharge=None, max_charge=None
        ))

if __name__ == '__main__':
    unittest.main()
