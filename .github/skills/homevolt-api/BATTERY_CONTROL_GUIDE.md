# Battery Control Guide

Complete guide for controlling the Tibber ECU battery system via the local API and console commands.

**API Version:** `stable_2512_1`

---

## Table of Contents

1. [Overview](#overview)
2. [Control Methods](#control-methods)
3. [Direct Control (Immediate)](#direct-control-immediate)
4. [Scheduled Control](#scheduled-control)
5. [Fetching Schedules](#fetching-schedules)
6. [Complete Examples](#complete-examples)
7. [Best Practices](#best-practices)

---

## Overview

The Tibber ECU provides two distinct methods for controlling battery charge/discharge behavior:

* `sched_set` replace the current schedule with a single new entry.
* `sched_add` add a new schedule entry to the schedule.

### ⚠️ Important: Local Mode Requirement

**To prevent remote partners (like Tibber) from overriding your local schedules, you MUST enable local mode:**

> **💡 Tip**: Use `param_list` in the console to see all available parameters including `settings_local` with its current value and description.

```bash
# Enable local mode to prevent remote schedule overrides
param_set settings_local 1
# Persist it to survive a restart
param_store
```

**Via HTTP:**
```bash
curl -u admin:<password> -X POST http://device.local/params.json \
  -H "Content-Type: application/json" \
  -d '{"settings_local":1}'
```

When `settings_local` is disabled (0), any schedule sent from Tibber or other partners via MQTT will **replace your local schedules**. Enable local mode to maintain full local control.

---

## Control Methods

### Available Control Modes

Both control methods support multiple operational modes:

| Mode | Type Value | Description |
|------|------------|-------------|
| **Idle** | `0` | Battery standby (no charge/discharge) |
| **Inverter Charge** | `1` | Charge battery via inverter from grid/solar |
| **Inverter Discharge** | `2` | Discharge battery via inverter to home/grid |
| **Grid Charge** | `3` | Charge from grid with power setpoint |
| **Grid Discharge** | `4` | Discharge to grid with power setpoint |
| **Grid Charge/Discharge** | `5` | Bidirectional grid control |
| **Frequency Reserve** | `6` | Frequency regulation service mode |
| **Solar Charge** | `7` | Charge from solar production only |
| **Solar Charge/Discharge** | `8` | Solar-based grid management |
| **Full Solar Export** | `9` | Export all solar production |

### Power Limits

Control commands accept power limits in **Watts**:

- **Positive values**: Maximum power for the operation
- **0**: Use system defaults or no limit
- **Range**: Typically 0-11000W (depends on inverter and battery capacity)

---

## Schedule Control

Use either `sched_set` or `sched_add`. They use the same arguments.

> **ℹ️ Command Reference**: Use the built-in `help <command>` for most accurate information. For example `help sched_add`.

### Console Command

```bash
sched_set <type> [OPTIONS]
```

**Required Arguments:**

- `<type>`: Schedule type (integer)
  - `0` = Idle
  - `1` = Inverter Charge
  - `2` = Inverter Discharge
  - `3` = Grid Charge
  - `4` = Grid Discharge
  - `5` = Grid Charge/Discharge
  - `6` = Frequency Reserve
  - `7` = Solar Charge
  - `8` = Solar Charge/Discharge
  - `9` = Full Solar Export

**Optional Arguments:**

**Time Constraints:**
- `--from <time>`: Start time (YYYY-MM-DDTHH:mm:ss)
- `--to <time>`: End time (YYYY-MM-DDTHH:mm:ss)

**SOC Constraints:**
- `--min <percent>`: Minimum state of charge (%)
- `--max <percent>`: Maximum state of charge (%)

**Power Settings:**
- `-s, --setpoint <watts>`: Power setpoint (W)
- `-d, --max_discharge <watts>`: Maximum discharge power (W)
- `-c, --max_charge <watts>`: Maximum charge power (W)

**Frequency Control Reserve (FCR) Settings:**
- `-n, --fcr_n_power <watts>`: FCR-N maximum power
- `-u, --fcr_d_up_power <watts>`: FCR-D-UP maximum power
- `-w, --fcr_d_down_power <watts>`: FCR-D-DOWN maximum power
- `-f, --ffr_power <watts>`: FFR maximum power
- `-m, --use_ffr_custom_trig_freq`: Use custom trigger frequency
- `-a, --ffr_rearm`: Rearm FFR after timeout
- `--fcr_start_from <time>`: Frequency service start time

**Solar/Grid Thresholds:**
- `-i, --idle_threshold_power <watts>`: Idle threshold power
- `-r, --discharge_threshold_power <watts>`: Discharge threshold power

**Power Limits:**
- `-l, --import_limit <watts>`: Grid import limit
- `-x, --export_limit <watts>`: Grid export limit

**Dynamic Load Balancing:**
- `--main_fuse <milliamps>`: Main fuse size (mA)
- `--charge_ramp_up <ma_per_sec>`: Charge ramp up rate (mA/s)
- `--discharge_ramp_up <ma_per_sec>`: Discharge ramp up rate (mA/s)

**Energy Limits:**
- `--import_energy_limit <wh>`: Energy import limit (Wh)
- `--import_energy_limit_from <time>`: Import limit start time
- `--import_energy_limit_to <time>`: Import limit end time
- `--import_energy_max_compensation <watts>`: Max compensation power
- `--export_energy_limit <wh>`: Energy export limit (Wh)
- `--export_energy_limit_from <time>`: Export limit start time
- `--export_energy_limit_to <time>`: Export limit end time
- `--export_energy_max_compensation <watts>`: Max compensation power

**Frequency Test Settings:**
- `-t, --test_sequence <id>`: Frequency test sequence (0-16, see below)
- `-e, --test_end_schedule`: End schedule after test completion

**Frequency Test Sequences:**
- `0` = NONE
- `1` = FCR_N_STEP
- `2` = FCR_N_STEP_ENDURANCE
- `3` = FCR_D_UP_RAMP
- `4` = FCR_D_UP_RAMP_ENDURANCE
- `5` = FCR_D_DOWN_RAMP
- `6` = FCR_D_DOWN_RAMP_ENDURANCE
- `7` = FCR_N_SINE
- `8` = FCR_D_UP_SINE
- `9` = FCR_D_DOWN_SINE
- `10` = FCR_N_LER
- `11` = FCR_D_UP_LER
- `12` = FCR_D_DOWN_LER
- `13` = FFR_STEP_49_5
- `14` = FFR_STEP_49_6
- `15` = FFR_STEP_49_7
- `16` = FFR_RAMP

**Idle Mode Settings:**
- `-o, --offline`: Take inverter offline during idle mode

### Examples

#### Basic Inverter Charge
```bash
# Console - Simple inverter charge at 3000W
ecu> sched_set 1 -s 3000
Setting immediate battery mode: INVERTER CHARGE at 3000W

# Charges battery from grid/solar at up to 3000W
```

#### Inverter Discharge with Power Limit
```bash
# Console - Discharge at 2000W
ecu> sched_set 2 -s 2000
Setting immediate battery mode: INVERTER DISCHARGE at 2000W

# Discharges battery at up to 2000W to home/grid
```

#### Inverter Charge with SOC Limits
```bash
# Console - Charge until 90% SOC
ecu> sched_set 1 -c 3000 --max 90
Setting battery to charge up to 90% SOC at max 3000W

# Stops charging when battery reaches 90%
```

#### Grid Charge with Setpoint
```bash
# Console - Grid charge at specific setpoint
ecu> sched_set 3 -s 2500
Setting grid charge at 2500W

# Charges from grid at 2500W setpoint
# Note: Type 3 = Grid Charge (requires setpoint)
```

#### Solar Charge Mode
```bash
# Console - Solar charge with max limit
ecu> sched_set 7 -c 4000
Setting solar charge mode with 4000W max

# Charges from solar only, up to 4000W
```

#### Solar Charge/Discharge with Grid Setpoint
```bash
# Console - Solar-based grid management
ecu> sched_set 8 -s 0 -c 3000 -d 2000
Setting solar charge/discharge: grid setpoint 0W, charge 3000W, discharge 2000W

# Maintains 0W grid import/export using battery
# Max charge 3000W, max discharge 2000W
```

#### Set Battery to Idle
```bash
# Console - Idle mode
ecu> sched_set 0
Setting battery to IDLE mode

# Battery enters standby - no charging or discharging
```

#### Idle with Inverter Offline
```bash
# Console - Idle mode with inverter offline
ecu> sched_set 0 -o
Setting battery to IDLE mode (inverter offline)

# Battery and inverter completely offline
```

### Via HTTP API

Direct control is **only available via console commands**. There is no dedicated HTTP endpoint for `sched_set`.

You can use the `/console.json` endpoint to execute console commands via HTTP:

```bash
# Execute sched_set via console.json endpoint
curl -u admin:<password> -X POST http://device.local/console.json \
  -H "Content-Type: application/json" \
  -d '{"cmd":"sched_set 1 -c 3000 --max 90"}'
```

```bash
# Execute sched_add via console.json endpoint
curl -u admin:<password> -X POST http://device.local/console.json \
  -H "Content-Type: application/json" \
  -d '{"cmd":"sched_add 1 --from 2025-12-15T23:00:00 --to 2025-12-16T07:00:00 -c 3000 --max 80"}'
```

### Examples

#### Schedule Night Charging (11 PM - 7 AM)

```bash
# Console command - charge during cheap night hours
ecu> sched_add 1 --from 2025-12-15T23:00:00 --to 2025-12-16T07:00:00 -c 3000 --max 80

# Explanation:
# - Type 1 = INVERTER CHARGE
# - Starts at 11 PM tonight
# - Ends at 7 AM tomorrow
# - Max charge power 3000W
# - Stop at 80% SOC
```

**Result:** Battery will charge from 11 PM to 7 AM at up to 3000W, stopping when SOC reaches 80%.

#### Schedule Peak Discharge (5 PM - 8 PM)

```bash
# Console command - discharge during peak pricing
ecu> sched_add 2 --from 2025-12-15T17:00:00 --to 2025-12-15T20:00:00 -d 2500 --min 30

# Explanation:
# - Type 2 = INVERTER DISCHARGE
# - Starts at 5 PM today
# - Ends at 8 PM today
# - Max discharge power 2500W
# - Stop at 30% SOC (preserve battery)
```

**Result:** Battery discharges during peak hours (5-8 PM) at up to 2500W, stopping at 30% SOC to preserve battery health.

#### Schedule Solar Charge/Discharge

```bash
# Console command - solar-based grid management during day
ecu> sched_add 8 --from 2025-12-16T10:00:00 --to 2025-12-16T16:00:00 -s 0 -c 4000 -d 3000

# Explanation:
# - Type 8 = SOLAR CHARGE/DISCHARGE
# - Starts tomorrow at 10 AM
# - Ends at 4 PM
# - Grid setpoint 0W (zero import/export)
# - Max charge 4000W, max discharge 3000W
```

**Result:** Battery manages grid import/export to maintain 0W grid power using solar production.

#### Schedule Grid Charge with Energy Limit

```bash
# Console command - night charge with energy limit
ecu> sched_add 3 --from 2025-12-15T23:00:00 --to 2025-12-16T07:00:00 \
  -s 3000 --import_energy_limit 20000 \
  --import_energy_limit_from 2025-12-15T23:00:00 \
  --import_energy_limit_to 2025-12-16T07:00:00

# Explanation:
# - Type 3 = GRID CHARGE
# - Time window: 11 PM to 7 AM
# - Setpoint: 3000W
# - Energy limit: 20000 Wh (20 kWh) during the period
```

**Result:** Battery charges from grid at 3000W but stops after importing 20 kWh total energy.

#### Schedule with SOC Range

```bash
# Console command - charge within SOC range
ecu> sched_add 1 --from 2025-12-15T23:00:00 --to 2025-12-16T07:00:00 \
  -c 3000 --min 20 --max 80

# Explanation:
# - Type 1 = INVERTER CHARGE
# - Only charge if SOC is between 20% and 80%
# - Max charge power 3000W
```

**Result:** Schedule only executes if battery SOC is in the 20-80% range.

#### Add Multiple Schedules (Weekly Pattern)

```bash
# Add charging schedule for next 7 nights
ecu> sched_add 1 --from 2025-12-15T23:00:00 --to 2025-12-16T07:00:00 -c 3000 --max 80
ecu> sched_add 1 --from 2025-12-16T23:00:00 --to 2025-12-17T07:00:00 -c 3000 --max 80
ecu> sched_add 1 --from 2025-12-17T23:00:00 --to 2025-12-18T07:00:00 -c 3000 --max 80
# ... continue for remaining days
```

⚠️ **Note**: Each schedule is a single event. For recurring patterns, you must add individual schedule entries for each occurrence.

---

## Fetching Schedules

### List All Active Schedules

**Console Command:**
```bash
ecu> sched_list
```

**Sample Output:**
```
Active Schedules (3):

ID: 1
  Start: 2025-12-19 23:00:00 (1703001600)
  Duration: 480 minutes
  Mode: CHARGE
  Power: 3000W
  SOC Target: 80%
  Status: PENDING

ID: 2
  Start: 2025-12-19 17:00:00 (1702998000)
  Duration: 180 minutes
  Mode: DISCHARGE
  Power: 2500W
  SOC Target: 30%
  Status: ACTIVE

ID: 3
  Start: 2025-12-20 12:00:00 (1703044800)
  Duration: 240 minutes
  Mode: CHARGE
  Power: 5000W
  SOC Target: 100%
  Status: PENDING
```

### Via HTTP API

**Endpoint:** `GET /schedule.json`

**Response:**
```json
{
  "local_mode": false,
  "schedule_id": "Manual Schedule",
  "schedule": [
    {
      "id": 1,
      "from": 1734303600,
      "to": 1734328800,
      "min": 20,
      "max": 90,
      "type": 1,
      "params": {
        "setpoint": 3000
      }
    },
    {
      "id": 2,
      "from": 1734361200,
      "to": 1734372000,
      "type": 2,
      "params": {
        "setpoint": 2500,
        "import_limit": 5000
      }
    }
  ]
}
```

**Response Fields:**
- `local_mode`: Boolean indicating if local mode is enabled (prevents remote MQTT schedules)
- `schedule_id`: String identifier for the schedule set (e.g., "Manual Schedule")
- `schedule`: Array of schedule objects
  - `id`: Schedule ID number
  - `from`: Start time (Unix timestamp)
  - `to`: End time (Unix timestamp)
  - `min`: Minimum SOC % (if SOC condition is set)
  - `max`: Maximum SOC % (if SOC condition is set)
  - `type`: Schedule type (0-9, see schedule types above)
  - `params`: Object containing schedule-specific parameters
    - `setpoint`: Power setpoint in Watts (for grid/inverter modes)
    - `max_charge`: Maximum charge power in Watts
    - `max_discharge`: Maximum discharge power in Watts
    - `import_limit`: Grid import limit in Watts
    - `export_limit`: Grid export limit in Watts
    - `offline`: Boolean for idle mode offline setting
    - Plus FCR/FFR and energy limit parameters if configured

---

## Managing Schedules

### Enable Local Mode (Prevent Remote Overrides)

**⚠️ Critical**: Before creating local schedules, enable local mode to prevent remote schedule overrides:

**Console Command:**
```bash
ecu> param_set settings_local 1
Parameter 'settings_local' set to 1
```

**HTTP API:**
```bash
curl -u admin:<password> -X POST http://device.local/params.json \
  -H "Content-Type: application/json" \
  -d '{"settings_local":1}'
```

**What settings_local does:**
- `0` (disabled): Remote schedules from Tibber/partners via MQTT **will replace** local schedules
- `1` (enabled): Remote schedules are **blocked**, only local schedules are used

**Check current status:**
```bash
# Console
ecu> param_get settings_local

# HTTP (params.json uses parameter name)
curl -u admin:<password> http://device.local/params.json | grep settings_local

# Or check in schedule.json response (uses 'local_mode' as JSON key)
curl -u admin:<password> http://device.local/schedule.json | grep local_mode
```

### Delete a Schedule

**Console Command:**
```bash
ecu> sched_del <schedule_id>

# Example
ecu> sched_del 2
Schedule ID 2 deleted
```

**HTTP API:**

⚠️ Schedule deletion is NOT available via HTTP DELETE. Use console commands only.

```bash
# Execute sched_del via console.json endpoint
curl -u admin:<password> -X POST http://device.local/console.json \
  -H "Content-Type: application/json" \
  -d '{"cmd":"sched_del 2"}'
```

### Clear All Schedules

**Console Command:**
```bash
ecu> sched_clear

# Warning: Removes ALL schedules
All schedules cleared
```

### Modify a Schedule

⚠️ **Note**: Schedules cannot be modified directly. To change a schedule:

1. Delete the existing schedule: `sched_del <id>`
2. Add a new schedule with updated parameters: `sched_add ...`

---

## Complete Examples

### Example 1: Time-of-Use Optimization

**Goal**: Charge battery during cheap night hours, discharge during expensive evening hours.

```bash
# Night charging (11 PM - 6 AM, charge to 90%)
ecu> sched_add 1 --from 2025-12-15T23:00:00 --to 2025-12-16T06:00:00 -c 3500 --max 90

# Evening discharge (5 PM - 9 PM, discharge to 20%)
ecu> sched_add 2 --from 2025-12-15T17:00:00 --to 2025-12-15T21:00:00 -d 3000 --min 20

# Verify schedules
ecu> sched_list
```

### Example 2: Solar Self-Consumption

**Goal**: Ensure battery charges during solar peak, holds charge for evening use.

```bash
# Midday solar charging (11 AM - 3 PM, type 7 = solar charge)
ecu> sched_add 7 --from 2025-12-15T11:00:00 --to 2025-12-15T15:00:00 -c 5000 --max 100

# Evening hold (6 PM - 10 PM, idle mode)
ecu> sched_add 0 --from 2025-12-15T18:00:00 --to 2025-12-15T22:00:00
```

### Example 3: Emergency Discharge Test

**Goal**: Test battery discharge capability immediately.

```bash
# Immediate discharge test at 2000W (type 2 = inverter discharge)
ecu> sched_set 2 -d 2000 --min 40

# Monitor for test duration, then return to idle
# ... wait for test completion ...

ecu> sched_set 0  # Return to idle mode
```

### Example 4: Grid Outage Preparation

**Goal**: Ensure battery is fully charged before predicted outage.

```bash
# Charge to 100% immediately (type 1 = inverter charge)
ecu> sched_set 1 -c 5000 --max 100

# Once charged, set to idle to preserve charge
ecu> sched_set 0
```

### Example 5: Solar Zero-Export Control

**Goal**: Use battery to maintain zero grid export during solar production.

```bash
# Solar charge/discharge mode for daytime (8 AM - 6 PM)
ecu> sched_add 8 --from 2025-12-15T08:00:00 --to 2025-12-15T18:00:00 \
  -s 0 -c 4000 -d 3000 --min 20 --max 90

# Explanation:
# - Type 8 = Solar Charge/Discharge
# - Grid setpoint 0W (zero export)
# - Max charge 4000W from solar
# - Max discharge 3000W to cover load
# - Keep SOC between 20-90%
```

---

## API Reference

For detailed API endpoint documentation, see:

- [API Documentation](API_DOCUMENTATION.md) - Complete endpoint reference
- [Console Commands Reference](CONSOLE_COMMANDS_REFERENCE.md) - All console commands
- [Parameters Reference](PARAMETERS_REFERENCE.md) - System configuration

---

## Quick Reference Card

```
┌────────────────────────────────────────────────────────────────────┐
│                  BATTERY CONTROL QUICK REFERENCE                   │
├────────────────────────────────────────────────────────────────────┤
│ IMMEDIATE CONTROL (sched_set)                                      │
│   Inverter charge:    sched_set 1 -c 3000 --max 90                 │
│   Inverter discharge: sched_set 2 -d 2000 --min 20                 │
│   Grid charge:        sched_set 3 -s 3000                          │
│   Solar charge:       sched_set 7 -c 4000                          │
│   Solar zero-export:  sched_set 8 -s 0 -c 4000 -d 3000             │
│   Idle mode:          sched_set 0                                  │
│   Idle offline:       sched_set 0 -o                               │
├────────────────────────────────────────────────────────────────────┤
│ SCHEDULED CONTROL (sched_add)                                      │
│   Same arguments as sched_set, but add time constraints:           │
│                                                                    │
│   Night charge:                                                    │
│     sched_add 1 --from 2025-12-15T23:00:00                         │
│                 --to 2025-12-16T07:00:00 -c 3000 --max 80          │
│                                                                    │
│   Peak discharge:                                                  │
│     sched_add 2 --from 2025-12-15T17:00:00                         │
│                 --to 2025-12-15T20:00:00 -d 2500 --min 20          │
├────────────────────────────────────────────────────────────────────┤
│ SCHEDULE MANAGEMENT                                                │
│   List all:        sched_list                                      │
│   Delete one:      sched_del <id>                                  │
├────────────────────────────────────────────────────────────────────┤
│ TYPES:                                                             │
│   0=Idle  1=Inv-Charge  2=Inv-Discharge  3=Grid-Charge             │
│   4=Grid-Discharge  5=Grid-Both  6=Freq-Reserve                    │
│   7=Solar-Charge  8=Solar-Both  9=Full-Solar-Export                │
│                                                                    │
│ COMMON OPTIONS:                                                    │
│   -s, --setpoint <W>      Power setpoint (grid modes)              │
│   -c, --max_charge <W>    Max charge power                         │
│   -d, --max_discharge <W> Max discharge power                      │
│   --min <percent>         Minimum SOC                              │
│   --max <percent>         Maximum SOC                              │
│   --from <time>           Start time (YYYY-MM-DDTHH:mm:ss)         │
│   --to <time>             End time (YYYY-MM-DDTHH:mm:ss)           │
│                                                                    │
│ SOC RANGE: 20-90% recommended for battery health                   │
└────────────────────────────────────────────────────────────────────┘
```

---

**Version:** `stable_2512_1`

**Last Updated:** December 2025

**Status:** ⚠️ Pre-stable API (subject to change)
