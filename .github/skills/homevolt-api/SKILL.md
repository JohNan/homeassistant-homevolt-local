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

**Official Source**: https://github.com/tibber/homevolt-local-api-doc

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ems.json` | GET | Battery, solar, inverter, grid status - main data source |
| `/status.json` | GET | System health and operational status |
| `/schedule.json` | GET | Current charging schedule |
| `/params.json` | GET | System parameters |
| `/nodes.json` | GET | Network nodes (CT clamps) |

## Energy Data Fields

### Battery Energy (Use These!)

| Field | Location | Unit | Description |
|-------|----------|------|-------------|
| `ems_aggregate.imported_kwh` | Per inverter | kWh | Energy charged INTO battery |
| `ems_aggregate.exported_kwh` | Per inverter | kWh | Energy discharged FROM battery |

**Important**: Use `ems_aggregate` values for battery energy - they match the Homevolt UI exactly.

### Raw Inverter Counters (Reference Only)

| Field | Location | Unit | Description |
|-------|----------|------|-------------|
| `ems_data.energy_consumed` | Per inverter | Wh | Raw inverter energy in counter |
| `ems_data.energy_produced` | Per inverter | Wh | Raw inverter energy out counter |

**Note**: `ems_data` values are raw inverter counters and will differ from `ems_aggregate` by ~15-20% due to inverter efficiency losses.

### CT Sensor Energy

| Field | Location | Unit | Description |
|-------|----------|------|-------------|
| `sensors[].energy_imported` | CT sensors | kWh | Energy imported (grid/solar/load) |
| `sensors[].energy_exported` | CT sensors | kWh | Energy exported (grid/solar/load) |

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
├── inverters[]           # Array of inverter objects
│   ├── battery_soc       # Battery state of charge (%)
│   ├── battery_soh       # Battery state of health (%)
│   ├── battery_power     # Current battery power (W)
│   ├── ems_data          # Raw inverter counters
│   │   ├── energy_consumed   # Wh (raw counter)
│   │   └── energy_produced   # Wh (raw counter)
│   └── aggregated        # Processed totals (USE THESE!)
│       └── ems_aggregate
│           ├── imported_kwh  # kWh charged
│           └── exported_kwh  # kWh discharged
├── sensors[]             # CT clamp sensors
│   ├── name              # "grid", "solar", "load"
│   ├── power             # Current power (W)
│   ├── energy_imported   # kWh imported
│   └── energy_exported   # kWh exported
└── totals                # System-wide totals
    ├── battery_soc       # Average SOC
    ├── battery_power     # Total battery power
    ├── grid_power        # Total grid power
    └── solar_power       # Total solar power
```

## Example API Response Structure

```json
{
  "inverters": [
    {
      "serial": "INV001",
      "battery_soc": 75,
      "battery_soh": 100,
      "battery_power": -1500,
      "ems_data": {
        "energy_consumed": 5234567,
        "energy_produced": 4567890
      },
      "aggregated": {
        "ems_aggregate": {
          "imported_kwh": 4234.5,
          "exported_kwh": 3890.2
        }
      }
    }
  ],
  "sensors": [
    {
      "name": "grid",
      "power": 500,
      "energy_imported": 12345.6,
      "energy_exported": 1234.5
    }
  ],
  "totals": {
    "battery_soc": 75,
    "battery_power": -1500,
    "grid_power": 500,
    "solar_power": 2000
  }
}
```

## Common Implementation Patterns

### Getting Battery Energy (Correct Way)

```python
# For total system
total_charged = sum(
    inv.aggregated.ems_aggregate.imported_kwh
    for inv in data.inverters
)
total_discharged = sum(
    inv.aggregated.ems_aggregate.exported_kwh
    for inv in data.inverters
)

# Per inverter
for inv in data.inverters:
    charged = inv.aggregated.ems_aggregate.imported_kwh      # kWh
    discharged = inv.aggregated.ems_aggregate.exported_kwh   # kWh
```

### Getting Grid/Solar/Load Power

```python
def get_sensor_by_name(sensors: list, name: str):
    return next((s for s in sensors if s.name == name), None)

grid = get_sensor_by_name(data.sensors, "grid")
solar = get_sensor_by_name(data.sensors, "solar")
load = get_sensor_by_name(data.sensors, "load")

grid_power = grid.power if grid else 0
solar_power = solar.power if solar else 0
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
