# System Parameters Reference

This document provides a comprehensive reference for all system parameters available in the Tibber ECU. Parameters are organized by functional group and define the behavior of the energy control system.

> **ℹ️ Live Parameter Discovery**: For the most up-to-date list of available parameters on your device, use the console command `param_list`. This will show all parameters with their current values, types, defaults, and help text as implemented in your firmware version.

## Table of Contents

- [Parameter Overview](#parameter-overview)
- [Access Levels](#access-levels)
- [Parameter Types](#parameter-types)
- [ECU Parameters](#ecu-parameters)
- [EMS Parameters](#ems-parameters)
- [HMI Parameters](#hmi-parameters)
- [System Parameters](#system-parameters)
- [MQTT Parameters](#mqtt-parameters)
- [API Usage](#api-usage)

## Parameter Overview

The ECU provides **41 system parameters** across 5 functional groups:

| Group | Count | Purpose |
|-------|-------|---------|
| ECU Parameters | 21 | Energy management, PID tuning, grid codes, power limits |
| EMS Parameters | 3 | Modbus communication, polling intervals, fuse sizing |
| HMI Parameters | 5 | LED strip visual modes and brightness control |
| System Parameters | 4 | Operational modes, provisioning, network identity |
| MQTT Parameters | 6 | Data transmission interval configuration |

## Access Levels

All parameters have one of two access levels:

| Level | Description | Access Path |
|-------|-------------|------------|
| **ALL** | Publicly readable, no authentication required | Readable without credentials |
| **ADMIN** | Requires admin authentication to read or modify | Requires `admin:<password>` in Basic Auth |

## Parameter Types

The following data types are used for parameters:

| Type | Description | Example |
|------|-------------|---------|
| BOOLEAN | True/false value | `true`, `false` |
| UINT8 | Unsigned 8-bit integer (0-255) | `10` |
| UINT16 | Unsigned 16-bit integer (0-65535) | `8000` |
| UINT32 | Unsigned 32-bit integer (0-4294967295) | `1000000` |
| UINT64 | Unsigned 64-bit integer | `9223372036854775807` |
| SINT8 | Signed 8-bit integer (-128 to 127) | `-50` |
| SINT32 | Signed 32-bit integer | `-100000` |
| SINT64 | Signed 64-bit integer | `-9223372036854775808` |
| FLT | Single precision float | `0.25`, `1.5e-3` |
| DOUBLE | Double precision float | `0.123456789` |
| STR32 | String up to 32 characters | `"192.168.1.1"` |

---

## ECU Parameters

**Group:** `ecu_params` | **Count:** 21 parameters | **Access:** ADMIN

Energy Control Unit parameters manage the battery system operation, including PID tuning, power limits, grid codes, and EMS communication.

### ems_pid_tune
- **Type:** FLT array [P, I, D, anti_windup, cutoff_hz]
- **Description:** PID tune values for the ECU power controller
- **Default:** `[0.25, 0.2, 0.1, 10.0, 0.25]`
- **Usage:** Fine-tunes the main energy balance control loop

### ems_load_balance_pid_tune
- **Type:** FLT array [P, I, D, anti_windup, cutoff_hz]
- **Description:** PID tune values for load balance controller
- **Default:** `[300.0, 150.0, 0.0, 1.0, 0.25]`
- **Usage:** Controls power distribution among devices in the system

### ems_idle_power_threshold
- **Type:** UINT16
- **Description:** Power threshold (Watts) for EMS to consider system idle
- **Default:** `80`
- **Range:** 0-65535
- **Usage:** Threshold below which the system is considered in standby

### ems_server
- **Type:** STR32
- **Description:** IP address or DNS name of EMS (Energy Management System) server
- **Default:** `""`
- **Usage:** Remote server connection for external energy control coordination

### ems_psk
- **Type:** UINT8 array (16 bytes)
- **Description:** Pre-shared key for EMS communication encryption
- **Default:** All zeros
- **Usage:** Security credentials for EMS server connection

### ems_grid_code_preset
- **Type:** UINT16
- **Description:** Grid code preset selection for grid synchronization
- **Default:** `1`
- **Values:**
  - `1` = Sweden
  - `2` = Germany
  - Other region-specific grid codes
- **Usage:** Determines voltage/frequency synchronization behavior

### ems_control_timeout
- **Type:** UINT16
- **Description:** Control timeout in seconds (0 = disabled)
- **Default:** `30`
- **Usage:** Maximum time to wait for EMS control commands before fallback

### ems_freq_report_mqtt_period
- **Type:** UINT16
- **Description:** Frequency report MQTT publication period (seconds)
- **Default:** `10`
- **Usage:** How often to report grid frequency via MQTT

### settings_local
- **Type:** BOOLEAN
- **Description:** Enable local mode (prevents remote MQTT schedules)
- **Default:** `false`
- **Usage:** When true, local settings override remote MQTT commands

### ecu_main_fuse_size_a
- **Type:** UINT8
- **Description:** Home main fuse size in Amperes
- **Default:** `0` (auto-detect)
- **Range:** 0-255
- **Usage:** Limits maximum system current based on electrical installation

### inverter_ffr_test_trigger_freq
- **Type:** UINT16
- **Description:** FFR (Fast Frequency Response) test trigger frequency (0.01% units)
- **Default:** `9996` (99.96 Hz)
- **Range:** 0-65535
- **Usage:** Frequency threshold at which FFR control is triggered

### ffr_rearm_timeout_s
- **Type:** UINT16
- **Description:** FFR rearm timeout in seconds
- **Default:** `900`
- **Usage:** Cooldown period before FFR system can be triggered again

### export_limitation_w
- **Type:** UINT32
- **Description:** Property export limitation in Watts (0 = unlimited)
- **Default:** `0`
- **Usage:** Maximum power allowed to export to the grid

### import_limitation_w
- **Type:** UINT32
- **Description:** Property import limitation in Watts (0 = unlimited)
- **Default:** `0`
- **Usage:** Maximum power allowed to import from the grid

### pid_history_select
- **Type:** UINT16
- **Description:** Select which PID loop to record history for debugging
- **Default:** `0`
- **Values:**
  - `0` = Disabled
  - `1` = Grid PID
  - `2-4` = Load balance charge PIDs
  - `5-7` = Load balance discharge PIDs
  - `8` = Export limitation PID
  - `9` = Import limitation PID
- **Usage:** Diagnostic tool for analyzing PID controller behavior

### export_limitation_pid_tune
- **Type:** FLT array [P, I, D, anti_windup, cutoff_hz]
- **Description:** PID tuning for export limitation controller
- **Default:** `[0.5, 0.2, 0.1, 1.0, 0.25]`
- **Usage:** Controls gradual power reduction when approaching export limit

### import_limitation_pid_tune
- **Type:** FLT array [P, I, D, anti_windup, cutoff_hz]
- **Description:** PID tuning for import limitation controller
- **Default:** `[0.5, 0.2, 0.1, 1.0, 0.25]`
- **Usage:** Controls gradual power reduction when approaching import limit

### energy_limitation_tune
- **Type:** FLT array [tau, k, m, comp_eagerness]
- **Description:** Energy limitation (kWh per hour) tuning parameters
- **Default:** `[10.0, 0.4, 0.7, 0.8]`
- **Usage:** Controls how aggressively to enforce energy limits

### import_energy_limit_wh
- **Type:** UINT32
- **Description:** Hourly import energy limit in Wh (0 = disabled)
- **Default:** `0`
- **Usage:** Maximum total energy allowed to import per hour

### fallback_charge_limit_w
- **Type:** UINT32
- **Description:** Fallback charge limit in W when grid sensor unavailable
- **Default:** `0`
- **Usage:** Safety limit for charging when grid data is not available

### fallback_discharge_limit_w
- **Type:** UINT32
- **Description:** Fallback discharge limit in W when grid sensor unavailable
- **Default:** `0`
- **Usage:** Safety limit for discharging when grid data is not available

---

## EMS Parameters

**Group:** `ems_params` | **Count:** 3 parameters | **Access:** ADMIN

EMS (Energy Management System) parameters control communication with external battery management and inverter systems.

### modbus_enable
- **Type:** BOOLEAN
- **Description:** Enable Modbus communication to BMS (Battery Management System) and Inverter
- **Default:** `true`
- **Usage:** Must be enabled for system to control battery and inverter

### ems_poll_interval_ms
- **Type:** UINT32 array
- **Description:** Poll intervals (milliseconds) for EMS communication
- **Array Order:**
  1. System data polling
  2. System info polling
  3. Battery data polling
  4. Battery info polling
  5. Control commands
  6. Configuration updates
  7. Mode selection
  8. Pending versions
- **Default:** `[100, 10000, 5000, 10000, 10000, 30000, 30000, 30000]`
- **Usage:** Tune communication frequency based on system responsiveness needs

### ecu_group_fuse_size_a
- **Type:** UINT8
- **Description:** Battery system group fuse size in Amperes
- **Default:** `0` (auto-detect)
- **Range:** 0-255
- **Usage:** Limits battery system current based on component ratings

---

## HMI Parameters

**Group:** `hmi_params` | **Count:** 5 parameters | **Access:** ADMIN

HMI (Human Machine Interface) parameters control the LED indicator strip visual feedback.

### ledstrip_mode
- **Type:** STR32
- **Description:** LED strip visual mode selection
- **Default:** `"off"`
- **Allowed Values:**
  - `"off"` - LED strip disabled
  - `"on"` - Solid color
  - `"soc"` - State of charge visualization
  - `"dem"` - Demand visualization
  - `"ser"` - Service status indication  <!-- codespell:ignore ser -->
  - `""` - Empty string to disable override (use hardware default)
- **Usage:** Selects what information is displayed on the LED indicator

### ledstrip_bright_max
- **Type:** UINT32
- **Description:** Maximum LED brightness level
- **Default:** `70`
- **Range:** 0-100
- **Usage:** Limits brightness to prevent visual glare

### ledstrip_bright_min
- **Type:** UINT32
- **Description:** Minimum LED brightness level
- **Default:** `20`
- **Range:** 0-100
- **Usage:** Ensures LEDs remain visible in dark environments

### ledstrip_mode_on_hue
- **Type:** UINT32
- **Description:** LED hue color when in "on" mode
- **Default:** `280`
- **Range:** 0-360 (HSV color wheel)
- **Usage:** Sets the color of the LED indicator (purple at 280°)

### ledstrip_mode_on_saturation
- **Type:** UINT32
- **Description:** LED color saturation (color intensity)
- **Default:** `100`
- **Range:** 0-100
- **Usage:** `100` = fully saturated color, `0` = white

---

## System Parameters

**Group:** `system_params` | **Count:** 4 parameters | **Access:** Mixed

System-level parameters controlling operational modes and network identity.

### provreg_enable
- **Type:** BOOLEAN
- **Description:** Enable automatic provisioning from server
- **Default:** `true`
- **Access:** ADMIN
- **Usage:** When enabled, device can be remotely provisioned with certificates and settings

### system_service_mode
- **Type:** BOOLEAN
- **Description:** Force ECU into service mode
- **Default:** `false`
- **Access:** ADMIN
- **Usage:** Enables extended diagnostics and bypass some safety checks for troubleshooting

### system_standalone_mode
- **Type:** BOOLEAN
- **Description:** Force ECU into standalone mode (disables server communication)
- **Default:** `false`
- **Access:** ADMIN
- **Usage:** System operates independently without remote control or monitoring

### ecu_mdns_instance_name
- **Type:** STR32
- **Description:** mDNS instance name on local network
- **Default:** `"Homevolt"`
- **Access:** ADMIN
- **Usage:** Device becomes discoverable as `<name>.local` on the network

---

## MQTT Parameters

**Group:** `mqtt_params` | **Count:** 6 parameters | **Access:** ADMIN

MQTT parameters control how frequently data is published to the cloud via MQTT.

### mqtt_log_send_interval_ms
- **Type:** UINT32 array
- **Description:** Log data transmission intervals (milliseconds)
- **Array Order:**
  1. Normal operation interval
  2. Service mode interval
- **Default:** `[5000, 1000]`
- **Usage:** Log messages sent at these intervals (more frequent in service mode)

### mqtt_metrics_send_interval_ms
- **Type:** UINT32 array
- **Description:** Metrics (statistics) transmission intervals (milliseconds)
- **Array Order:**
  1. Normal operation interval
  2. Service mode interval
- **Default:** `[120000, 5000]`
- **Usage:** Periodic metric updates (e.g., energy counters, efficiency)

### mqtt_node_data_send_interval_ms
- **Type:** UINT32 array
- **Description:** Node/sensor data transmission intervals (milliseconds)
- **Array Order:**
  1. Normal operation interval
  2. Service mode interval
- **Default:** `[10000, 1000]`
- **Usage:** Updates from wireless sensor nodes in network

### mqtt_settings_send_interval_ms
- **Type:** UINT32 array
- **Description:** Settings synchronization intervals (milliseconds)
- **Array Order:**
  1. Normal operation interval
  2. Service mode interval
- **Default:** `[60000, 5000]`
- **Usage:** Periodic sync of active parameter settings to cloud

### mqtt_status_report_send_interval_ms
- **Type:** UINT32 array
- **Description:** Status report transmission intervals (milliseconds)
- **Array Order:**
  1. Normal operation interval
  2. Service mode interval
- **Default:** `[60000, 60000]`
- **Usage:** System health and status updates

### mqtt_ems_data_send_interval_ms
- **Type:** UINT32 array
- **Description:** EMS/BMS data transmission intervals (milliseconds)
- **Array Order:**
  1. Normal operation interval
  2. Service mode interval
- **Default:** `[10000, 10000]`
- **Usage:** Battery and inverter status updates

---

## API Usage

### Reading Parameters

**Endpoint:** `GET /params.json`

Returns all system parameters organized by group.

```bash
curl -u admin:<password> http://device.local/params.json | jq .
```

**Response Structure:**
```json
{
  "ecu_params": {
    "ems_pid_tune": [0.25, 0.2, 0.1, 10.0, 0.25],
    "ems_idle_power_threshold": 80,
    ...
  },
  "ems_params": {
    "modbus_enable": true,
    ...
  },
  "hmi_params": {...},
  "system_params": {...},
  "mqtt_params": {...}
}
```

### Setting Parameters

**Endpoint:** `POST /params.json`

Updates a single parameter value.

**Form Parameters:**
- `k` - Parameter key (e.g., `ems_idle_power_threshold`)
- `v` - New value as string
- `store` - 0 (runtime only) or 1 (save to persistent storage)

```bash
# Set power threshold to 100W (runtime only)
curl -u admin:<password> -d "k=ems_idle_power_threshold&v=100&store=0" \
  http://device.local/params.json

# Persist LED mode to storage
curl -u admin:<password> -d "k=ledstrip_mode&v=on&store=1" \
  http://device.local/params.json
```

### Console Commands

Parameters can also be queried and set via the console API using parameter commands:

```
ecu> param_get ems_idle_power_threshold
80

ecu> param_set ems_idle_power_threshold 120
Parameter 'ems_idle_power_threshold' set to 120

ecu> param_list
(Lists all available parameters)
```

---

## Parameter Best Practices

1. **Persistent Storage**: Use `store=1` only for parameters you want to survive device restart
2. **PID Tuning**: Adjust PID values incrementally and monitor system stability
3. **Access Levels**: Only ADMIN-level users can modify security-sensitive parameters
4. **Service Mode**: Enable `system_service_mode` only during troubleshooting
5. **Grid Codes**: Changing `ems_grid_code_preset` requires system restart
6. **MQTT Intervals**: Shorter intervals increase network traffic; balance with responsiveness needs

---

## See Also

- [API Documentation](API_DOCUMENTATION.md) - Complete API endpoint reference
- [Console Commands Reference](CONSOLE_COMMANDS_REFERENCE.md) - Console API commands
