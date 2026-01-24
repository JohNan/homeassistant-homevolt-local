---
name: homevolt-api
description: Tibber Homevolt Local API knowledge including endpoints, data structures, energy fields, power sign conventions, and battery control. Use when working with Homevolt battery system integration, sensor data, energy monitoring, or API responses.
---

# Homevolt Local API Reference

This skill provides knowledge about the Tibber Homevolt Local API for developing the Home Assistant integration.

## Documentation Files (Local Copies)

The full API documentation is included in this skill folder:

- [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) - Complete API endpoint reference with examples
- [API_QUICK_REFERENCE.md](./API_QUICK_REFERENCE.md) - Quick endpoint reference and common patterns
- [PARAMETERS_REFERENCE.md](./PARAMETERS_REFERENCE.md) - System parameters reference (41 parameters)
- [BATTERY_CONTROL_GUIDE.md](./BATTERY_CONTROL_GUIDE.md) - Battery control and scheduling

## API Endpoints (Core)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/status.json` | GET | System health and operational status |
| `/logs.json` | GET | System logs |
| `/params.json` | GET/POST | List/set system parameters |
| `/node_params.json` | GET/POST | Get/set remote node parameters |
| `/validatepassword` | POST | Validate password strength |
| `/wifiscan.json` | GET | WiFi scan results |
| `/nodes.json` | GET | Network nodes (CT clamps) |
| `/node_data.json` | GET | Node electrical data |
| `/node_metrics.json` | GET | Node metrics |
| `/ct.json` | GET | Clamp measurements |
| `/ct_data.json` | GET | Versioned clamp data |
| `/ct_history.json` | GET | Clamp history |
| `/ems.json` | GET | EMS status (battery, solar, inverter, grid) |
| `/ems_history.json` | GET | Historical EMS data |
| `/ems_pid_history.json` | GET | PID controller debug data |
| `/schedule.json` | GET | Charging schedule |
| `/pid.json` | GET | PID controller state |
| `/efr_hub_status.json` | GET | Hub operational status |
| `/ecu_sense.json` | GET | Sensor function assignments |
| `/error_report.json` | GET | Current active errors |
| `/error_history.json` | GET | Historical error log |
| `/ota_manifest.json` | GET | OTA updates & progress |
| `/update` | POST | Upload firmware binary |
| `/spiffs/{filepath}` | GET | Download file |
| `/upload/spiffs/{filepath}` | POST | Upload file |
| `/delete/spiffs/{filepath}` | POST | Delete file |
| `/console.json` | POST | Execute CLI command |
| `/mains_data.json` | GET | Mains voltage/frequency |
| `/warp_ping.json` | GET | Mesh network ping stats |

**Official Source**: https://github.com/tibber/homevolt-local-api-doc

## Energy Data Fields

### Battery Energy (Use These!)

| Field | Location | Unit | Description |
|-------|----------|------|-------------|
| `ems_aggregate.imported_kwh` | Per EMS entry | kWh | Energy charged INTO battery |
| `ems_aggregate.exported_kwh` | Per EMS entry | kWh | Energy discharged FROM battery |

**Important**: Use `ems_aggregate` values for battery energy - they match the Homevolt UI exactly.

### Raw Inverter Counters (Reference Only)

| Field | Location | Unit | Description |
|-------|----------|------|-------------|
| `ems_data.energy_consumed` | Per EMS entry | Wh | Raw inverter energy in counter |
| `ems_data.energy_produced` | Per EMS entry | Wh | Raw inverter energy out counter |

**Note**: `ems_data` values are raw inverter counters and will differ from `ems_aggregate` by ~15-20% due to inverter efficiency losses.

### Sensor Energy (Function Sensors)

| Field | Location | Unit | Description |
|-------|----------|------|-------------|
| `sensors[].energy_imported` | Function sensors | kWh | Energy imported (grid/solar/load/battery) |
| `sensors[].energy_exported` | Function sensors | kWh | Energy exported (grid/solar/load/battery) |

## Power Sign Conventions

Understanding the sign conventions is critical for correct sensor implementation:

### Battery Power
- **Positive**: Discharging (energy flowing FROM battery TO home)
- **Negative**: Charging (energy flowing TO battery FROM grid/solar)

### Grid Power
- **Positive**: Importing from grid (consuming)
- **Negative**: Exporting to grid (selling back)

### Solar Power
- **Always Positive**: Solar production is always positive

## Data Structure Hierarchy

```
/ems.json
├── ems[]                 # Array of EMS entries (per ECU/inverter stack)
│   ├── ems_info           # Firmware, rated capacity/power
│   ├── ems_data           # Live measurements & raw counters
│   │   ├── power             # Current power (W)
│   │   ├── energy_produced   # Wh (raw counter)
│   │   └── energy_consumed   # Wh (raw counter)
│   └── ems_aggregate      # Processed totals (USE THESE!)
│       ├── imported_kwh   # kWh charged
│       └── exported_kwh   # kWh discharged
├── aggregated            # System-wide aggregated EMS values
│   └── ems_data           # Combined EMS data (power, energy, SOC, etc.)
└── sensors[]             # Function sensors (grid/solar/load/battery)
    ├── function           # "grid", "solar", "load", "battery"
    ├── total_power        # Current power (W)
    ├── energy_imported    # kWh imported
    └── energy_exported    # kWh exported
```

## Example API Response Structure

```json
{
  "ems": [
    {
      "ems_info": {
        "fw_version": "v31.4",
        "rated_capacity": 13304,
        "rated_power": 6000
      },
      "ems_data": {
        "power": -7,
        "energy_produced": 3602110,
        "energy_consumed": 4050829
      },
      "ems_aggregate": {
        "imported_kwh": 916.37,
        "exported_kwh": 4197.55
      }
    }
  ],
  "aggregated": {
    "ems_data": {
      "power": -10,
      "energy_produced": 5237025,
      "energy_consumed": 6177742
    }
  },
  "sensors": [
    {
      "function": "grid",
      "total_power": 3282,
      "energy_imported": 8337.99,
      "energy_exported": 7485
    }
  ]
}
```

## Common Implementation Patterns

### Getting Battery Energy (Correct Way)

```python
# For total system
total_charged = sum(
    ems.ems_aggregate.imported_kwh
    for ems in data.ems
)
total_discharged = sum(
    ems.ems_aggregate.exported_kwh
    for ems in data.ems
)

# Per EMS entry
for ems in data.ems:
    charged = ems.ems_aggregate.imported_kwh      # kWh
    discharged = ems.ems_aggregate.exported_kwh   # kWh
```

### Getting Grid/Solar/Load Power

```python
def get_sensor_by_function(sensors: list, function: str):
    return next((s for s in sensors if s.function == function), None)

grid = get_sensor_by_function(data.sensors, "grid")
solar = get_sensor_by_function(data.sensors, "solar")
load = get_sensor_by_function(data.sensors, "load")
grid_power = grid.total_power if grid else 0
solar_power = solar.total_power if solar else 0
load_power = load.total_power if load else 0
```

## Sensor Classification for Home Assistant

### Power Sensors (Instantaneous)
- Device class: `SensorDeviceClass.POWER`
- Unit: `UnitOfPower.WATT`
- State class: `SensorStateClass.MEASUREMENT`

### Energy Sensors (Cumulative)
- Device class: `SensorDeviceClass.ENERGY`
- Unit: `UnitOfEnergy.KILO_WATT_HOUR`
- State class: `SensorStateClass.TOTAL_INCREASING`

### Battery Percentage
- Device class: `SensorDeviceClass.BATTERY`
- Unit: `PERCENTAGE`
- State class: `SensorStateClass.MEASUREMENT`
