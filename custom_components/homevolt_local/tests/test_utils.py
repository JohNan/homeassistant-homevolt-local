from custom_components.homevolt_local.models import HomevoltData

def mock_homevolt_data(num_ems=1, num_sensors=1):
    """Generate mock HomevoltData."""
    ems_data = []
    for i in range(num_ems):
        ems_data.append({
            "ecu_id": f"ecu_{i}",
            "ems_data": {"state_str": "idle", "soc_avg": 50.0, "power": 100.0, "energy_produced": 1000.0, "energy_consumed": 500.0},
            "error_str": "",
            "inv_info": {"serial_number": f"inv_{i}"},
            "ems_info": {"fw_version": "1.0.0"}
        })

    sensors_data = []
    for i in range(num_sensors):
        sensors_data.append({
            "euid": f"sensor_{i}",
            "type": "grid",
            "total_power": 200.0,
            "energy_imported": 2000.0,
            "energy_exported": 1000.0,
            "available": True,
            "node_id": i
        })

    return HomevoltData.from_dict({
        "aggregated": {
            "ems_data": {"state_str": "idle", "soc_avg": 50.0, "power": 100.0, "energy_produced": 1000.0, "energy_consumed": 500.0},
            "error_str": "",
            "bms_data": [{"soc": 5000}]
        },
        "ems": ems_data,
        "sensors": sensors_data,
        "schedules": [],
        "schedule_count": 0,
        "schedule_current_id": ""
    })
