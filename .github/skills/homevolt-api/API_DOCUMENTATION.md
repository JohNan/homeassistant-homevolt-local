# Tibber ECU Webserver API Documentation

## Table of Contents

1. [Authentication](#authentication)
2. [Rate Limiting](#rate-limiting)
3. [API Endpoints](#api-endpoints)
   - [System & Status](#system--status)
   - [Configuration & Parameters](#configuration--parameters)
   - [Network & WiFi](#network--wifi)
   - [Nodes](#nodes)
   - [Energy Management](#energy-management)
   - [File Management](#file-management)
   - [OTA Updates](#ota-updates)
   - [Debugging & Console](#debugging--console)
4. [Battery Control Guide](#battery-control-guide)
5. [System Parameters Reference](#system-parameters-reference)

---

## Authentication

All endpoints except captive portal detection require **HTTP Basic Authentication**.

**Default Password**: By default, the webserver isn't enable nor have a password.

**Security Recommendation**: Set a custom webserver password via the device parameters for improved security.

### Example Request
```bash
curl -u admin:<password> http://homevolt-<deviceid>.local/params.json
```

### Response Codes
- **200 OK**: Request successful
- **401 Unauthorized**: Invalid credentials
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **500 Internal Server Error**: Server error

---

## Rate Limiting

Password authentication is protected with exponential backoff to prevent brute-force attacks. If this happens, wait before trying again.

---

## API Endpoints

### System & Status

#### GET /status.json
Returns overall system health and operational status.

**Request:**
```bash
curl -u admin:<password> http://homevolt-<deviceid>.local/status.json
```

**Response:**
```json
{
  "up_time": 335974780,
  "poll_time": 0,
  "firmware": {
    "esp": "3056-1a3446ed",
    "efr": "804-4190150b"
  },
  "wifi_status": {
    "wifi_mode": "sta",
    "ip": "192.168.2.221",
    "ssid": "JNET",
    "bssid": "18e829a7d731",
    "rssi": -43,
    "connected": true,
    "wifi_err_buf": [
      1006,
      1006
    ]
  },
  "lte_status": {
    "imei": "864145063230323",
    "imsi": "234502102103229",
    "iccid": "89457300000011033129",
    "operator": "\"24001\"",
    "operator_name": "Telia",
    "area_code": "\"355\"",
    "cell_id": "\"190FD1F\"",
    "band": "\"LTE BAND 3\"",
    "acc_tech": "eMTC",
    "sysmode": "eMTC",
    "rssi_db": -65,
    "rssi": 26,
    "ber": 99,
    "chan": 1300,
    "pdp_active": true,
    "sim_type": "CHIP",
    "f_pin_ok": true,
    "f_present": true,
    "scan_seq": "020301"
  },
  "mqtt_status": {
    "connected": true,
    "subscribed": true,
    "last_error": {
      "esp_tls_last_esp_err": 0,
      "esp_tls_stack_err": 0,
      "esp_tls_cert_verify_flags": 0,
      "error_type": 0,
      "connect_return_code": 0,
      "esp_transport_sock_errno": 0
    }
  },
  "ota_update_running": false,
  "w868_status": {
    "product_id": 57577,
    "efr_id": "f082c0fffec63065",
    "network_state": 2,
    "node_type": 1,
    "node_id": 0,
    "pan_id": 52903,
    "radio_channel": 11,
    "radio_power": 200
  },
  "ems_status": {
    "ems_info": {
      "protocol_version": 5,
      "fw_version": "v31.4",
      "rated_power": 6000,
      "rated_cap": 13304,
      "rated_pv_power": 0
    },
    "inverter_info": {
      "fw_version": "V1.10-97.0",
      "serial_number": "F412FAE4F3EC"
    },
    "bms_info": [
      {
        "fw_version": "v6",
        "serial_number": "80000274069924350025",
        "rated_cap": 6652,
        "id": 0,
        "battery_type": 1,
        "battery_type_str": "NMC 210 10A"
      },
      {
        "fw_version": "v6",
        "serial_number": "80000274089924410060",
        "rated_cap": 6652,
        "id": 1,
        "battery_type": 1,
        "battery_type_str": "NMC 210 10A"
      }
    ]
  }
}
```

---

#### GET /logs.json
Retrieves system log entries.

**Parameters:**
- `limit` (optional, int): Max log entries, default=100
- `level` (optional, string): Filter by level (DEBUG, INFO, WARNING, ERROR)

**Request:**
```bash
curl -u admin:<password> "http://homevolt-<deviceid>.local/logs.json?limit=50&level=ERROR"
```

**Response:**
```json
[
  {
    "timestamp": 1766131937963,
    "core": 1,
    "level": "debug",
    "data": "timesync_ts_tck: 2383765905",
    "tag": "wire_protocol_status",
    "task": "wire_rx_task"
  },
  {
    "timestamp": 1766131937965,
    "core": 1,
    "level": "debug",
    "data": "   ts_offset_ms: 1766059191175",
    "tag": "wire_protocol_status",
    "task": "wire_rx_task"
  }
]
```

---

### Configuration & Parameters

> **💡 Tip**: Use the `param_list` console command to see all available parameters with their current values, types, and documented use cases directly from the device.

#### GET /params.json
Lists all system parameters with current values, defaults, types, and constraints.

**Request:**
```bash
curl -u admin:<password> http://homevolt-<deviceid>.local/params.json
```

**Response:**
```json
[
  {
    "param_id": 4,
    "desc": "\"common_params\"",
    "name": "smart_cli_mode",
    "size": 1,
    "type": "bool",
    "value": [
      true
    ],
    "default": [
      false
    ],
    "help": "Enable smart CLI mode for terminal (Up/Down arrow for history, Tab for completion)",
    "level": 8
  },
  {
    "param_id": 15,
    "desc": "\"common_params\"",
    "name": "ota_enable_esp32",
    "size": 1,
    "type": "bool",
    "value": [
      true
    ],
    "default": [
      true
    ],
    "help": "Enable OTA for main esp32 chip",
    "level": 8
  },
  {
    "param_id": 21,
    "desc": "\"common_params\"",
    "name": "ota_enable_hub_web",
    "size": 1,
    "type": "bool",
    "value": [
      true
    ],
    "default": [
      true
    ],
    "help": "Enable OTA updates for the webapp",
    "level": 8
  }
]
```

---

#### POST /params.json
Sets a system parameter value.

**Request:**
```bash
curl -u admin:<password> -X POST \
  -d "k=battery_min_soc&v=25&store=1" \
  http://homevolt-<deviceid>.local/params.json
```

| Field | Required | Description |
|-------|----------|-------------|
| `k` | Yes | Parameter name |
| `v` | Yes | New value (will be converted to appropriate type) |
| `store` | No | 1=persist to NVS, 0=temporary (default) |

**Response:**
```
Saved parameter k: 'battery_min_soc' v: '25'
```

---

#### GET /node_params.json
Gets parameters for a remote node.

**Parameters:**
- `node_id` (required, int): node ID

**Request:**
```bash
curl -u admin:<password> "http://homevolt-<deviceid>.local/node_params.json?node_id=5"
```

---

#### POST /node_params.json
Sets parameters on a remote node.

**Parameters:**
- `node_id` (required, int): node ID

**Request Body:**
- `k` (string): Parameter name
- `v` (string): Parameter value

---

### Network & WiFi

#### GET /wifiscan.json
Returns list of available WiFi networks.

**Request:**
```bash
curl -u admin:<password> http://homevolt-<deviceid>.local/wifiscan.json
```

**Response:**
```json
[
  {
    "ssid": "JNEXT",
    "bssid": "18e829a7d341",
    "ch": 1,
    "open": false,
    "bw": "20",
    "rssi": -43,
    "auth": "wpa2",
    "gcipher": "ccmp",
    "pchiper": "ccmp",
    "11b": 0,
    "11g": 1,
    "11n": 1,
    "wps": 0
  },
  {
    "ssid": "",
    "bssid": "1ee829a7d341",
    "ch": 1,
    "open": false,
    "bw": "20",
    "rssi": -44,
    "auth": "wpa2",
    "gcipher": "ccmp",
    "pchiper": "ccmp",
    "11b": 1,
    "11g": 1,
    "11n": 1,
    "wps": 0
  },
  ...
```

**Signal Strength Guide:**
- **-30 to -50 dBm**: Excellent (very close)
- **-50 to -60 dBm**: Good
- **-60 to -70 dBm**: Fair
- **-70 to -80 dBm**: Weak
- **-80 dBm and below**: Very weak or unusable

---

### Captive Portal (No Authentication Required)

These endpoints are used by devices to detect and present a captive WiFi portal:

| Endpoint | Clients | Response |
|----------|---------|----------|
| GET `/generate_204*` | Apple, Android | 204 No Content |
| GET `/hotspot-detect.html` | Apple | 204 No Content |
| GET `/connecttest.txt` | Android | 204 No Content |
| GET `/ncsi.txt` | Windows | 204 No Content |
| GET `/redirect` | Generic | Redirect |

---

### Nodes

#### GET /nodes.json
Lists all discovered network nodes.

**Request:**
```bash
curl -u admin:<password> http://homevolt-<deviceid>.local/nodes.json
```

**Response:**
```json
[
  {
    "node_id": 1,
    "product_id": 53456,
    "product_model": "TBF01",
    "eui": "a46dd4fffee4dd49",
    "version": "1220-911ca807",
    "warp_version": 1,
    "average_rssi": -81,
    "rssi": -81,
    "average_lqi": 209,
    "lqi": 255,
    "pdr": 100,
    "last_seen_ms": 4908,
    "last_data_ms": 4911,
    "available": true,
    "ota_upload_state": "idle",
    "ota_distribute_status": "up2date",
    "paired": true,
    "advertise_sent": false,
    "model": "tibber-pulse-clamp-node-efr32-fg23",
    "ota_tag": 223,
    "manifest_version": "1220-911ca807"
  },
  {
    "node_id": 2,
    "product_id": 53456,
    "product_model": "TBF01",
    "eui": "a46dd4fffee50de5",
    "version": "1216-63cdc09f",
    "warp_version": 0,
    "average_rssi": 0,
    "rssi": 0,
    "average_lqi": 0,
    "lqi": 0,
    "pdr": 0,
    "last_seen_ms": 2147483647,
    "last_data_ms": 2147483647,
    "available": false,
    "ota_upload_state": "failed",
    "ota_distribute_status": "inactive_node",
    "paired": true,
    "advertise_sent": false,
    "model": "tibber-pulse-clamp-node-efr32-fg23",
    "ota_tag": 223,
    "manifest_version": "1220-911ca807"
  },
  {
    "node_id": 3,
    "product_id": 53456,
    "product_model": "TBF01",
    "eui": "9035eafffe2b0d31",
    "version": "1220-911ca807",
    "warp_version": 1,
    "average_rssi": -86,
    "rssi": -86,
    "average_lqi": 213,
    "lqi": 255,
    "pdr": 100,
    "last_seen_ms": 2517,
    "last_data_ms": 2520,
    "available": true,
    "ota_upload_state": "idle",
    "ota_distribute_status": "up2date",
    "paired": true,
    "advertise_sent": false,
    "model": "tibber-pulse-clamp-node-efr32-fg23",
    "ota_tag": 223,
    "manifest_version": "1220-911ca807"
  }
]
```
---

#### GET /node_metrics.json
Gets performance metrics for a node (battery, temperature, radio stats).

**Parameters:**
- `node_id` (required, int): node ID

**Request:**
```bash
curl -u admin:<password> "http://homevolt-<deviceid>.local/node_metrics.json?node_id=1"
```

**Response:**
```json
{
  "node": {
    "node_id": 1,
    "timestamp": 1766130654,
    "node_version": 0,
    "bootloader_version": 33554435,
    "battery_voltage": 2.96,
    "temperature": 12.59,
    "avg_rssi": -76.22,
    "avg_lqi": 255,
    "radio_tx_power": 200,
    "node_uptime": 2043675213,
    "meter_msg_count_sent": 61,
    "meter_pkg_count_sent": 61,
    "meter_msg_count_received": 61,
    "meter_pkg_count_received": 61,
    "time_in_em0_ms": 4805,
    "time_in_em1_ms": 1003,
    "time_in_em2_ms": 295271,
    "meter_mode": 0,
    "usb_power": true,
    "timesync_clock_drift": 327679
  },
  "hub": {
    "meter_pkg_count_sent": 0,
    "meter_msg_count_sent": 0,
    "meter_pkg_count_received": 61,
    "meter_msg_count_received": 61,
    "meter_corrupt_reading_count_received": 0
  },
  "packet_delivery_rate": 100
}
```

---

### Current Transformer (CT) Data

#### GET /ct.json
Gets latest clamp meter measurements.

**Parameters:**
- `node_id` (required, int): node ID

**Request:**
```bash
curl -u admin:<password> "http://homevolt-<deviceid>.local/ct.json?node_id=1"
```

**Response:**
```json
{
  "bs": 2348843008,
  "cs": 2348843008,
  "beb": 0,
  "ct": [
    {
      "ts": 1766130872134,
      "amps": 4.08,
      "volts": 238.63,
      "deg": 44.79,
      "ceb": 0,
      "csb": 0,
      "pf": 0.71,
      "va": 973.06,
      "pwr": 690.55,
      "line": 0,
      "imp": 98.25,
      "exp": 6.33
    },
    {
      "ts": 1766130872134,
      "amps": 2.13,
      "volts": 238.63,
      "deg": 71.54,
      "ceb": 0,
      "csb": 0,
      "pf": 0.32,
      "va": 507.69,
      "pwr": 160.74,
      "line": 240,
      "imp": 133.49,
      "exp": 6.88
    },
    {
      "ts": 1766130872134,
      "amps": 10.11,
      "volts": 238.63,
      "deg": 18.32,
      "ceb": 0,
      "csb": 0,
      "pf": 0.95,
      "va": 2411.5,
      "pwr": 2289.29,
      "line": 120,
      "imp": 104.67,
      "exp": 5.47
    }
  ],
  "tpw": 3140,
  "imp": 336.42,
  "exp": 18.68
}
```

---

#### GET /ct_data.json
Gets versioned clamp data with optional time filtering.

**Parameters:**
- `node_id` (required, int): node ID
- `from` (optional, int): Start timestamp
- `to` (optional, int): End timestamp

**Request:**
```bash
curl -u admin:<password> "http://homevolt-<deviceid>.local/ct_data.json?node_id=1&from=1703000000&to=1703080000"
```

---

#### GET /ct_history.json
Gets historical clamp measurements for trend analysis.

**Parameters:**
- `node_id` (required, int): node ID
- `limit` (optional, int): Number of entries, default=100
- `from` (optional, int): Start timestamp

**Request:**
```bash
curl -u admin:<password> "http://homevolt-<deviceid>.local/ct_history.json?node_id=1&limit=50"
```

---

### Energy Management

#### GET /ems.json
Returns comprehensive EMS status (battery, solar, inverter, grid).

**Request:**
```bash
curl -u admin:<password> http://homevolt-<deviceid>.local/ems.json
```

**Response:**
```json
{
  "$type": "ems_data",
  "ts": 1766130780,
  "ems": [
    {
      "ecu_id": "68b6b34cda94",
      "ecu_host": "",
      "ecu_version": "",
      "error": 0,
      "error_str": "No error",
      "op_state": 1,
      "op_state_str": "idle",
      "ems_info": {
        "protocol_version": 5,
        "fw_version": "v31.4",
        "rated_capacity": 13304,
        "rated_power": 6000,
        "rated_pv_power": 0,
        "model": "B6"
      },
      "bms_info": [
        {
          "fw_version": "v6",
          "serial_number": "80000274069924350025",
          "rated_cap": 6652,
          "id": 0,
          "battery_type": 1,
          "battery_type_str": "NMC 210 10A"
        },
        {
          "fw_version": "v6",
          "serial_number": "80000274089924410060",
          "rated_cap": 6652,
          "id": 1,
          "battery_type": 1,
          "battery_type_str": "NMC 210 10A"
        }
      ],
      "inv_info": {
        "fw_version": "V1.10-97.0",
        "serial_number": "F412FAE4F3EC"
      },
      "ems_config": {
        "grid_code_preset": 9,
        "grid_code_preset_str": "Sweden",
        "control_timeout": true
      },
      "inv_config": {
        "ffr_fstart_freq": 9900
      },
      "ems_control": {
        "mode_sel": 1,
        "mode_sel_str": "operational",
        "pwr_ref": 0,
        "freq_res_mode": 0,
        "freq_res_pwr_fcr_n": 0,
        "freq_res_pwr_fcr_d_up": 0,
        "freq_res_pwr_fcr_d_down": 0,
        "freq_res_pwr_ref_ffr": 0,
        "act_pwr_ch_lim": 6028,
        "act_pwr_di_lim": 0,
        "react_pwr_pos_limit": 7000,
        "react_pwr_neg_limit": 7000,
        "freq_test_seq": 0,
        "data_usage": 0,
        "allow_dfu": true
      },
      "ems_data": {
        "timestamp_ms": 1766130780000,
        "state": 4,
        "state_str": "Throttled",
        "info": 269,
        "info_str": [
          "EMS_INFO_FAN_STATE_ON",
          "EMS_INFO_CONNECTED_TO_BACKEND",
          "EMS_INFO_RTC_SYNCRONIZED",
          "EMS_INFO_LOW_POWER_MODE"
        ],
        "warning": 64,
        "warning_str": [
          "EMS_WARNING_UNDER_SOC_MIN_WARNING"
        ],
        "alarm": 0,
        "alarm_str": [],
        "phase_angle": 90,
        "frequency": 49998,
        "phase_seq": 1,
        "power": -7,
        "apparent_power": 7,
        "reactive_power": 0,
        "energy_produced": 3602110,
        "energy_consumed": 4050829,
        "sys_temp": 205,
        "avail_cap": 10817,
        "freq_res_state": 0,
        "soc_avg": 68
      },
      "bms_data": [
        {
          "energy_avail": 38,
          "cycle_count": 272,
          "soc": 70,
          "state": 5,
          "state_str": "Connected",
          "alarm": 0,
          "alarm_str": [],
          "tmin": 212,
          "tmax": 229
        },
        {
          "energy_avail": 36,
          "cycle_count": 271,
          "soc": 67,
          "state": 5,
          "state_str": "Connected",
          "alarm": 0,
          "alarm_str": [],
          "tmin": 214,
          "tmax": 237
        }
      ],
      "ems_prediction": {
        "avail_ch_pwr": 6028,
        "avail_di_pwr": 0,
        "avail_ch_energy": 10743,
        "avail_di_energy": 74,
        "avail_inv_ch_pwr": 6028,
        "avail_inv_di_pwr": 0,
        "avail_group_fuse_ch_pwr": 11040,
        "avail_group_fuse_di_pwr": 11040
      },
      "ems_voltage": {
        "l1": 2305,
        "l2": 2315,
        "l3": 2331,
        "l1_l2": 3997,
        "l2_l3": 4009,
        "l3_l1": 4032
      },
      "ems_current": {
        "l1": 0,
        "l2": 0,
        "l3": 0
      },
      "ems_aggregate": {
        "imported_kwh": 916.37,
        "exported_kwh": 4197.55
      },
      "error_cnt": 0
    },
    {
      "ecu_id": "188b0ec6106c",
      "ecu_host": "[2001:9B1:4447:F200:1A8B:EFF:FEC6:106C]:5259",
      "ecu_version": "",
      "error": 0,
      "error_str": "No error",
      "op_state": 1,
      "op_state_str": "idle",
      "ems_info": {
        "protocol_version": 5,
        "fw_version": "v31.4",
        "rated_capacity": 13304,
        "rated_power": 6000,
        "rated_pv_power": 0,
        "model": "B6"
      },
      "bms_info": [
        {
          "fw_version": "v4-44-g1413a7d",
          "serial_number": "80000274049924100024",
          "rated_cap": 6652,
          "id": 0,
          "battery_type": 1,
          "battery_type_str": "NMC 210 10A"
        },
        {
          "fw_version": "v4-44-g1413a7d",
          "serial_number": "80000274099925020047",
          "rated_cap": 6652,
          "id": 1,
          "battery_type": 1,
          "battery_type_str": "NMC 210 10A"
        }
      ],
      "inv_info": {
        "fw_version": "V1.10-97.0",
        "serial_number": "80000296119725083668"
      },
      "ems_config": {
        "grid_code_preset": 9,
        "grid_code_preset_str": "Sweden",
        "control_timeout": true
      },
      "inv_config": {
        "ffr_fstart_freq": 9900
      },
      "ems_control": {
        "mode_sel": 1,
        "mode_sel_str": "operational",
        "pwr_ref": 0,
        "freq_res_mode": 0,
        "freq_res_pwr_fcr_n": 0,
        "freq_res_pwr_fcr_d_up": 0,
        "freq_res_pwr_fcr_d_down": 0,
        "freq_res_pwr_ref_ffr": 0,
        "act_pwr_ch_lim": 6028,
        "act_pwr_di_lim": 0,
        "react_pwr_pos_limit": 7000,
        "react_pwr_neg_limit": 7000,
        "freq_test_seq": 0,
        "data_usage": 0,
        "allow_dfu": true
      },
      "ems_data": {
        "timestamp_ms": 1766130779000,
        "state": 4,
        "state_str": "Throttled",
        "info": 269,
        "info_str": [
          "EMS_INFO_FAN_STATE_ON",
          "EMS_INFO_CONNECTED_TO_BACKEND",
          "EMS_INFO_RTC_SYNCRONIZED",
          "EMS_INFO_LOW_POWER_MODE"
        ],
        "warning": 64,
        "warning_str": [
          "EMS_WARNING_UNDER_SOC_MIN_WARNING"
        ],
        "alarm": 0,
        "alarm_str": [],
        "phase_angle": 90,
        "frequency": 49996,
        "phase_seq": 1,
        "power": -3,
        "apparent_power": 3,
        "reactive_power": 0,
        "energy_produced": 1634915,
        "energy_consumed": 2126913,
        "sys_temp": 204,
        "avail_cap": 12216,
        "freq_res_state": 0,
        "soc_avg": 194
      },
      "bms_data": [
        {
          "energy_avail": 35,
          "cycle_count": 357,
          "soc": 59,
          "state": 5,
          "state_str": "Connected",
          "alarm": 0,
          "alarm_str": [],
          "tmin": 199,
          "tmax": 230
        },
        {
          "energy_avail": 202,
          "cycle_count": 142,
          "soc": 331,
          "state": 5,
          "state_str": "Connected",
          "alarm": 0,
          "alarm_str": [],
          "tmin": 198,
          "tmax": 218
        }
      ],
      "ems_prediction": {
        "avail_ch_pwr": 6028,
        "avail_di_pwr": 0,
        "avail_ch_energy": 11979,
        "avail_di_energy": 237,
        "avail_inv_ch_pwr": 6028,
        "avail_inv_di_pwr": 0,
        "avail_group_fuse_ch_pwr": 0,
        "avail_group_fuse_di_pwr": 0
      },
      "ems_voltage": {
        "l1": 2304,
        "l2": 2311,
        "l3": 2330,
        "l1_l2": 3995,
        "l2_l3": 4002,
        "l3_l1": 4031
      },
      "ems_current": {
        "l1": 0,
        "l2": 0,
        "l3": 0
      },
      "ems_aggregate": {
        "imported_kwh": 1211.98,
        "exported_kwh": 1599.11
      },
      "error_cnt": 0,
      "peer": {
        "last_seq": 629530,
        "last_timestamp_ms": 1766130780286,
        "last_decrypt_age_ms": 517,
        "last_encrypt_age_ms": 575
      }
    }
  ],
  "aggregated": {
    "error": 0,
    "error_str": "No error",
    "op_state": 1,
    "op_state_str": "idle",
    "ems_control": {
      "mode_sel": 1,
      "mode_sel_str": "operational",
      "pwr_ref": 0,
      "freq_res_mode": 0,
      "freq_res_pwr_fcr_n": 0,
      "freq_res_pwr_fcr_d_up": 0,
      "freq_res_pwr_fcr_d_down": 0,
      "freq_res_pwr_ref_ffr": 0,
      "act_pwr_ch_lim": 12056,
      "act_pwr_di_lim": 0,
      "react_pwr_pos_limit": 14000,
      "react_pwr_neg_limit": 14000,
      "freq_test_seq": 0,
      "data_usage": 0,
      "allow_dfu": true
    },
    "ems_data": {
      "timestamp_ms": 1766130780000,
      "state": 4,
      "state_str": "Throttled",
      "info": 269,
      "info_str": [
        "EMS_INFO_FAN_STATE_ON",
        "EMS_INFO_CONNECTED_TO_BACKEND",
        "EMS_INFO_RTC_SYNCRONIZED",
        "EMS_INFO_LOW_POWER_MODE"
      ],
      "warning": 64,
      "warning_str": [
        "EMS_WARNING_UNDER_SOC_MIN_WARNING"
      ],
      "alarm": 0,
      "alarm_str": [],
      "phase_angle": 90,
      "frequency": 49997,
      "phase_seq": 1,
      "power": -10,
      "apparent_power": 10,
      "reactive_power": 0,
      "energy_produced": 5237025,
      "energy_consumed": 6177742,
      "sys_temp": 204,
      "avail_cap": 23033,
      "freq_res_state": 0,
      "soc_avg": 131
    },
    "ems_prediction": {
      "avail_ch_pwr": 12056,
      "avail_di_pwr": 0,
      "avail_ch_energy": 22722,
      "avail_di_energy": 311,
      "avail_inv_ch_pwr": 12056,
      "avail_inv_di_pwr": 0,
      "avail_group_fuse_ch_pwr": 11040,
      "avail_group_fuse_di_pwr": 11040
    }
  },
  "sensors": [
    {
      "function": "battery",
      "sensor_type": "ems",
      "euid": "000068b6b34cda94",
      "interface": 0,
      "available": true,
      "rssi": 0,
      "average_rssi": 0,
      "pdr": 0,
      "phase": [
        {
          "voltage": 230.5,
          "amp": 0,
          "power": 0,
          "pf": 0
        },
        {
          "voltage": 231.5,
          "amp": 0,
          "power": 0,
          "pf": 0
        },
        {
          "voltage": 233.1,
          "amp": 0,
          "power": 0,
          "pf": 0
        }
      ],
      "frequency": 50,
      "total_power": -7,
      "energy_imported": 916.37,
      "energy_exported": 4197.55,
      "timestamp": 1766130780000,
      "timestamp_str": "2025-12-19 08:53:00.000"
    },
    {
      "function": "solar",
      "sensor_type": "pulse_ct",
      "node_id": 3,
      "euid": "9035eafffe2b0d31",
      "interface": 7,
      "available": true,
      "rssi": -87,
      "average_rssi": -86.65,
      "pdr": 100,
      "phase": [
        {
          "voltage": 230.4,
          "amp": 0.12,
          "power": 6.63,
          "pf": 0.24
        },
        {
          "voltage": 231.1,
          "amp": 0,
          "power": 0,
          "pf": 0
        },
        {
          "voltage": 233,
          "amp": 0,
          "power": 0,
          "pf": 0
        }
      ],
      "frequency": 49.95,
      "total_power": 6,
      "energy_imported": 13292.32,
      "energy_exported": 12.85,
      "timestamp": 1766130776133,
      "timestamp_str": "2025-12-19 08:52:56.133"
    },
    {
      "function": "grid",
      "sensor_type": "pulse_ct",
      "node_id": 1,
      "euid": "a46dd4fffee4dd49",
      "interface": 7,
      "available": true,
      "rssi": -81,
      "average_rssi": -81.46,
      "pdr": 100,
      "phase": [
        {
          "voltage": 230.4,
          "amp": 10.16,
          "power": 2235.02,
          "pf": 0.95
        },
        {
          "voltage": 231.2,
          "amp": 2.13,
          "power": 164.78,
          "pf": 0.34
        },
        {
          "voltage": 233,
          "amp": 4.73,
          "power": 882.42,
          "pf": 0.8
        }
      ],
      "frequency": 49.95,
      "total_power": 3282,
      "energy_imported": 8337.99,
      "energy_exported": 7485,
      "timestamp": 1766130778131,
      "timestamp_str": "2025-12-19 08:52:58.131"
    },
    {
      "function": "load",
      "sensor_type": "virtual",
      "euid": "0000000000000000",
      "interface": 0,
      "available": true,
      "rssi": 0,
      "average_rssi": 0,
      "pdr": 0,
      "phase": [
        {
          "voltage": 230.4,
          "amp": 10.28,
          "power": -2369.15,
          "pf": -1
        },
        {
          "voltage": 231.2,
          "amp": 2.13,
          "power": -491.87,
          "pf": -1
        },
        {
          "voltage": 233,
          "amp": 4.73,
          "power": -1101.56,
          "pf": -1
        }
      ],
      "frequency": 49.95,
      "total_power": -3278,
      "energy_imported": 489.16,
      "energy_exported": 14019.34,
      "timestamp": 1766130780000,
      "timestamp_str": "2025-12-19 08:53:00.000"
    },
    {
      "function": "battery",
      "sensor_type": "ems",
      "euid": "0000188b0ec6106c",
      "interface": 0,
      "available": true,
      "rssi": 0,
      "average_rssi": 0,
      "pdr": 0,
      "phase": [
        {
          "voltage": 230.4,
          "amp": 0,
          "power": 0,
          "pf": 0
        },
        {
          "voltage": 231.1,
          "amp": 0,
          "power": 0,
          "pf": 0
        },
        {
          "voltage": 233,
          "amp": 0,
          "power": 0,
          "pf": 0
        }
      ],
      "frequency": 50,
      "total_power": -3,
      "energy_imported": 1211.98,
      "energy_exported": 1599.11,
      "timestamp": 1766130779000,
      "timestamp_str": "2025-12-19 08:52:59.000"
    }
  ]
}
```

**Power Sign Convention:**
- **Battery**: Positive = discharge, Negative = charge
- **Grid**: Positive = import, Negative = export
- **Inverter**: Always positive (generation)
- **Solar**: Always positive (generation)

---

#### GET /ems_history.json
Retrieves historical EMS data points.

**Parameters:**
- `limit` (optional, int): Number of points, default=1000
- `from` (optional, int): Start timestamp

**Request:**
```bash
curl -u admin:<password> "http://homevolt-<deviceid>.local/ems_history.json?limit=100"
```

---

#### GET /ems_pid_history.json
Gets PID controller debug data for algorithm tuning.

**Parameters:**
- `limit` (optional, int): Number of entries, default=500

---

**Response:**
```json
{
  "from": 0,
  "id": 1,
  "name": "ems_pid",
  "constants": {
    "kp": 0.25,
    "ki": 0.2,
    "kd": 0.1,
    "setpoint": -6000,
    "anti_windup": 10,
    "cutoff_hz": 0.25
  },
  "data": {}
}
````

#### GET /schedule.json
Returns current charging schedule.

**Request:**
```bash
curl -u admin:<password> http://homevolt-<deviceid>.local/schedule.json
```

**Response:**
```json
{
  "local_mode": false,
  "schedule_id": "6a4ee454-20c5-45f4-9dde-2da6d4e53417",
  "schedule": [
    {
      "id": 1,
      "from": 1766131200,
      "to": 1766132100,
      "type": 1,
      "params": {
        "main_fuse": 25000,
        "charge_ramp_up": 1000,
        "discharge_ramp_up": 1000,
        "import_energy_limit_to": 1766134800,
        "import_energy_limit": 6000,
        "setpoint": 6000
      }
    },
    {
      "id": 2,
      "from": 1766132100,
      "to": 1766133000,
      "type": 3,
      "params": {
        "main_fuse": 25000,
        "charge_ramp_up": 1000,
        "discharge_ramp_up": 1000,
        "import_energy_limit_from": 1766131200,
        "import_energy_limit_to": 1766134800,
        "import_energy_limit": 6000,
        "setpoint": 0
      }
    },
    {
      "id": 3,
      "from": 1766133000,
      "to": 1766134800,
      "type": 1,
      "params": {
        "main_fuse": 25000,
        "charge_ramp_up": 1000,
        "discharge_ramp_up": 1000,
        "import_energy_limit_from": 1766131200,
        "import_energy_limit": 6000,
        "setpoint": 6000
      }
    }
  ]
}
```

---

#### GET /pid.json
Returns current PID controller parameters and states, if you like to adjust the tuning using pid parameters.

**Request:**
```bash
curl -u admin:<password> http://homevolt-<deviceid>.local/pid.json
```

**Response:**
```json
{
  "ems_pid": {
    "kp": 0.25,
    "ki": 0.2,
    "kd": 0.1,
    "setpoint": 0,
    "integral": 64292.87,
    "filtered_input": -1205.71,
    "prev_error": 1205.71,
    "anti_windup": 10,
    "cutoff_hz": 0.25,
    "prev_output": 0,
    "prev_input": -977.92,
    "prev_min": -12056,
    "prev_max": 0,
    "prev_delta_t": 1,
    "prev_timestamp_ms": 71969000
  },
  "lb_charge": {
    "kp": 300,
    "ki": 150,
    "kd": 0,
    "setpoint": 25,
    "integral": 80.37,
    "filtered_input": 4.41,
    "prev_error": 20.59,
    "anti_windup": 1,
    "cutoff_hz": 0.25,
    "prev_output": 12056,
    "prev_input": 3.66,
    "prev_min": 0,
    "prev_max": 12056,
    "prev_delta_t": 1,
    "prev_timestamp_ms": 71969000
  },
  "lb_discharge": {
    "kp": 300,
    "ki": 150,
    "kd": 0,
    "setpoint": 25,
    "integral": 0,
    "filtered_input": -2.13,
    "prev_error": 27.13,
    "anti_windup": 1,
    "cutoff_hz": 0.25,
    "prev_output": 0,
    "prev_input": -2.13,
    "prev_min": 0,
    "prev_max": 0,
    "prev_delta_t": 1,
    "prev_timestamp_ms": 71969000
  }
}
```

---

### Hub & Subsystem Status

#### GET /efr_hub_status.json
Returns W868/EFR hub operational status.

**Request:**
```bash
curl -u admin:<password> http://homevolt-<deviceid>.local/efr_hub_status.json
```

**Response:**
```json
{
  "product_id": 57577,
  "efr_id": "f082c0fffec63065",
  "network_state": 2,
  "node_type": 1,
  "node_id": 0,
  "pan_id": 52903,
  "radio_channel": 11,
  "radio_power": 200,
  "version": "804-4190150b",
  "bl_version": 2,
  "permit_pairing": false,
  "permit_pairing_timeout": 0,
  "warp_mode": 1,
  "timesync_ts_ticks": 2357173847,
  "ts_offset": 1766059191140,
  "ota": {
    "taget_id": 0,
    "image_tag": 0,
    "status": 0,
    "is_distr": 0,
    "image_size": 0,
    "req_start": 0,
    "req_end": 0,
    "resp_start": 0,
    "resp_end": 0
  }
}
```

---

#### GET /ecu_sense.json
Returns sensor function assignments and calibration.

**Request:**
```bash
curl -u admin:<password> http://homevolt-<deviceid>.local/ecu_sense.json
```

**Response:**
```json
[
  {
    "node_euid": "9035eafffe2b0d31",
    "interface": 7,
    "interface_names": [
      "L1",
      "L2",
      "L3"
    ],
    "function": 2,
    "function_name": "solar",
    "label": ""
  },
  {
    "node_euid": "a46dd4fffee4dd49",
    "interface": 7,
    "interface_names": [
      "L1",
      "L2",
      "L3"
    ],
    "function": 1,
    "function_name": "grid",
    "label": ""
  },
  {
    "node_euid": "a46dd4fffee50de5",
    "interface": 7,
    "interface_names": [
      "L1",
      "L2",
      "L3"
    ],
    "function": 0,
    "function_name": "unspecified",
    "label": ""
  }
]
```

---

### Error Management

#### GET /error_report.json
Returns active error states across all subsystems.

**Request:**
```bash
curl -u admin:<password> http://homevolt-<deviceid>.local/error_report.json
```

**Response:**
```json
[
  {
    "sub_system_id": 0,
    "sub_system_name": "ECU",
    "error_id": 1,
    "error_name": "power_24v",
    "activated": "ok",
    "message": "",
    "details": []
  },
  {
    "sub_system_id": 0,
    "sub_system_name": "ECU",
    "error_id": 2,
    "error_name": "ledstrip_detected",
    "activated": "ok",
    "message": "Rev:2 (461 mV)",
    "details": []
  }
]
```

**Severity Levels:**
- `INFO`: Informational message
- `WARNING`: Non-critical issue
- `ERROR`: System error
- `CRITICAL`: System-critical failure

---

#### GET /error_history.json
Retrieves historical error log entries.

**Parameters:**
- `limit` (optional, int): Number of entries, default=100
- `severity` (optional, string): Filter (INFO, WARNING, ERROR, CRITICAL)

**Request:**
```bash
curl -u admin:<password> "http://homevolt-<deviceid>.local/error_history.json?limit=50&severity=ERROR"
```

---

### OTA Updates

#### GET /ota_manifest.json
Returns available OTA updates and progress.

**Request:**
```bash
curl -u admin:<password> http://homevolt-<deviceid>.local/ota_manifest.json
```

**Response:**
```json
{
  "timestamp": 1703079600,
  "updates": [
    {
      "product_id": 1,
      "current_version": "1.2.3",
      "available_version": "1.2.4",
      "file_size": 524288,
      "manifest_url": "https://...",
      "state": "IDLE",
      "progress_percent": 0,
      "up2date": false
    }
  ]
}
```

**Update States:**
- `IDLE`: No update in progress
- `DOWNLOADING`: Fetching firmware
- `VERIFYING`: Validating firmware integrity
- `INSTALLING`: Flashing firmware
- `COMPLETE`: Update successful
- `ERROR`: Update failed

---

#### POST /update
Uploads firmware binary for OTA update.

**Request:**
```bash
curl -u admin:<password> -X POST \
  --data-binary @firmware.bin \
  http://homevolt-<deviceid>.local/update
```

**Response:**
```json
{
  "status": "success",
  "message": "Firmware uploaded, installation will begin shortly"
}
```

---

### File Management & Storage

#### GET /spiffs/{filepath}
Downloads a file from SPIFFS filesystem.

**Parameters:**
- `filepath` (required, string): File path (e.g., `config/data.json`)

**Request:**
```bash
curl -u admin:<password> http://homevolt-<deviceid>.local/spiffs/config/settings.json -o settings.json
```

---

#### POST /upload/spiffs/{filepath}
Uploads a file to SPIFFS filesystem.

**Parameters:**
- `filepath` (required, string): Destination path

**Request:**
```bash
curl -u admin:<password> -X POST \
  --data-binary @local_file.txt \
  http://homevolt-<deviceid>.local/upload/spiffs/backup/file.txt
```

**Response:**
```json
{
  "status": "success",
  "filename": "file.txt",
  "size": 2048
}
```

---

#### POST /delete/spiffs/{filepath}
Deletes a file from SPIFFS filesystem.

**Parameters:**
- `filepath` (required, string): File path to delete

**Request:**
```bash
curl -u admin:<password> -X POST \
  http://homevolt-<deviceid>.local/delete/spiffs/backup/old_file.txt
```

---

### Debugging & Console

#### POST /console.json
Executes a CLI command and returns output.

**Request:**
```bash
curl -u admin:<password> -X POST \
  -d "cmd=status" \
  http://homevolt-<deviceid>.local/console.json
```

**Response:**
```t
ecu-hub-esp32>  param_store 65
Command 'param_store 65' executed successfully
```

**Common Commands:**
- `help` - List available commands
- `status` - System status
- `restart` - Reboot system
- `reset` - Factory reset
- `version` - Show firmware version
- `uptime` - System uptime

---

### Measurements & Data

#### GET /mains_data.json
Returns mains voltage and frequency measurements.

**Parameters:**
- `timestamp` (optional, int): Specific timestamp to query

**Request:**
```bash
curl -u admin:<password> http://homevolt-<deviceid>.local/mains_data.json
```

**Response:**
```json
{
  "timestamp": 2371354624,
  "peak_index": 95,
  "signal_voltage": 0,
  "mains_voltage": 336.08,
  "mains_voltage_rms": 237.64,
  "average_voltage": 89.95,
  "frequency": 49.95,
  "avg_max": 3838,
  "avg_min": 0,
  "noise": 0,
  "mains_adc_buffer": []
}
```

---

#### GET /warp_ping.json
Returns network ping statistics.

**Request:**
```bash
curl -u admin:<password> http://homevolt-<deviceid>.local/warp_ping.json
```

**Response:**
```json
[
  {
    "type": "outgoing_ping",
    "source": 0,
    "destination": 1,
    "flags": 8,
    "index": 0,
    "ping_send_timestamp": 0,
    "ping_recv_timestamp": 0,
    "ping_recv_rssi": 0,
    "ping_recv_lqi": 0,
    "pong_recv_timestamp": 0,
    "pong_recv_rssi": 0,
    "pong_recv_lqi": 0
  },
  {
    "type": "outgoing_ping",
    "source": 0,
    "destination": 1,
    "flags": 8,
    "index": 1,
    "ping_send_timestamp": 0,
    "ping_recv_timestamp": 0,
    "ping_recv_rssi": 0,
    "ping_recv_lqi": 0,
    "pong_recv_timestamp": 0,
    "pong_recv_rssi": 0,
    "pong_recv_lqi": 0
  }
]
```

---

## Response Codes Reference

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 204 | No Content | Success, no response body |
| 302 | Found | Redirect |
| 400 | Bad Request | Invalid parameters |
| 401 | Unauthorized | Missing/invalid credentials |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 500 | Internal Error | Server error |
| 507 | Insufficient Storage | Storage full |

---

## Usage Examples

### Get Battery Status
```bash
curl -u admin:<password> http://homevolt-<deviceid>.local/ems.json | jq '.battery_soc'
```

### Monitor Grid Power in Real-Time
```bash
watch -n 2 'curl -s -u admin:<password> http://homevolt-<deviceid>.local/ems.json | jq ".grid_power"'
```

### Download Recent Logs
```bash
curl -u admin:<password> http://homevolt-<deviceid>.local/logs.json?limit=200 > logs.json
```

### Set Battery Minimum SOC
```bash
curl -u admin:<password> -X POST \
  -d "k=battery_min_soc&v=30&store=1" \
  http://homevolt-<deviceid>.local/params.json
```

### Execute Diagnostic Command
```bash
curl -u admin:<password> -X POST \
  -d "cmd=diagnostic" \
  http://homevolt-<deviceid>.local/console.json | jq '.output'
```

---

## Troubleshooting

### 401 Unauthorized
- Check username is `admin`
- Verify password matches QR code on device
- Check password hasn't been changed

### 503 Service Unavailable
- System may be starting up or updating
- Check system status with `/status.json`
- Try again after 30 seconds

### Timeout on Large Requests
- Some endpoints (like `/logs.json` with high limit) may be slow
- Reduce `limit` parameter
- Increase request timeout

### No Nodes Appearing
- Check EFR hub is powered and connected
- Verify nodes have power and are in range
- Check `/efr_hub_status.json` for hub status

---

## Security Notes

1. **Always use HTTPS in production** (enable with config setting)
2. **Change default QR-code password** as soon as possible
3. **Use strong, unique passwords** (minimum 12 characters recommended)
4. **Protect local network access** - don't expose to untrusted networks
5. **Monitor authentication logs** for suspicious activity
6. **Keep firmware updated** - check `/ota_manifest.json` regularly

---

## Battery Control Guide

The ECU provides powerful battery control capabilities through both immediate and scheduled operations.

### Quick Start

**Direct Control (Immediate):**
```bash
# Force charge at 3000W
ecu> sched_set 1 3000 0

# Return to auto mode
ecu> sched_set 0 0 0
```

**Scheduled Control (Time-based):**
```bash
# Schedule night charging (11 PM - 7 AM, charge to 80%)
START=$(date -d "today 23:00" +%s)
ecu> sched_add $START 480 1 3000 80
```

### Key Differences

| Feature | Direct (`sched_set`) | Scheduled (`sched_add`) |
|---------|---------------------|------------------------|
| **Execution** | Immediate | Time-based |
| **Persistence** | Lost on reboot | Survives reboot |
| **Use Case** | Testing, manual override | Automation, recurring patterns |
| **Access** | Console only | Console + API |

### Control Modes

- **0** = Auto (ECU decides)
- **1** = Charge (force battery charging)
- **2** = Discharge (force battery discharge)
- **3** = Idle (battery standby)

### Managing Schedules

```bash
# List all schedules
ecu> sched_list

# Delete a schedule
ecu> sched_del <id>

# Clear all schedules
ecu> sched_clear
```

### Complete Documentation

For comprehensive battery control documentation, including:
- Detailed command reference
- Complete real-world examples
- Time-of-use optimization strategies
- Best practices for battery health
- Troubleshooting guide

📖 **See: [BATTERY_CONTROL_GUIDE.md](BATTERY_CONTROL_GUIDE.md)**

---

## System Parameters Reference

The ECU provides **41 configurable system parameters** organized into 5 functional groups:

### Parameter Groups

| Group | Count | Purpose |
|-------|-------|---------|
| **ECU Parameters** | 21 | Energy management, PID tuning, grid codes, power limits |
| **EMS Parameters** | 3 | Modbus communication, polling intervals, fuse sizing |
| **HMI Parameters** | 5 | LED strip visual modes and brightness control |
| **System Parameters** | 4 | Operational modes, provisioning, network identity |
| **MQTT Parameters** | 6 | Data transmission interval configuration |

### Quick Reference

All parameters are accessible via the `/params.json` endpoint:

```bash
# List all parameters
GET /params.json

# Set a parameter (runtime only)
POST /params.json
  k=parameter_name
  v=new_value
  store=0

# Persist parameter to storage
POST /params.json
  k=parameter_name
  v=new_value
  store=1
```

### Key Parameters

**Energy Control:**
- `ems_pid_tune` - Main controller PID tuning
- `ems_idle_power_threshold` - Idle detection threshold
- `export_limitation_w` - Maximum export power
- `import_limitation_w` - Maximum import power

**LED Indicator:**
- `ledstrip_mode` - Display mode (off|on|soc|dem|ser)  <!-- codespell:ignore ser -->
- `ledstrip_bright_max` / `ledstrip_bright_min` - Brightness limits
- `ledstrip_mode_on_hue` - Color selection (0-360°)

**System Operation:**
- `system_service_mode` - Enable service diagnostics
- `system_standalone_mode` - Disable remote control
- `provreg_enable` - Auto-provisioning

**MQTT Transmission:**
- `mqtt_*_send_interval_ms` - Data transmission intervals

### Full Documentation

For complete parameter descriptions, default values, and configuration examples, see:

📖 **[PARAMETERS_REFERENCE.md](PARAMETERS_REFERENCE.md)** - Comprehensive parameter guide

---

## Support

For issues or questions:
- Check device logs: `GET /logs.json`
- Review error report: `GET /error_report.json`
- Execute diagnostic: `POST /console.json` with `cmd=diagnostic`
- Contact Tibber support: https://www.tibber.com/support
