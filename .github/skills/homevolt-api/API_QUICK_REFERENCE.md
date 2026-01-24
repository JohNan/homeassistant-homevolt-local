# API Quick Reference Guide

**Tibber ECU Local Webserver API** Version `stable_2512_1`

**Subject to change between versions**  Stable API coming 2026

**Enable API** Contact Tibber support

## Endpoints by Category

### System & Status (3 endpoints)
```
GET  /status.json              → System health overview
GET  /logs.json                → System log entries
```

### Configuration (4 endpoints)
```
GET  /params.json              → List all parameters
POST /params.json              → Set parameter value
GET  /node_params.json         → Get remote node parameters (requires node_id)
POST /node_params.json         → Set remote node parameters (requires node_id)
```

### Authentication (1 endpoint)
```
POST /validatepassword         → Validate password strength
```

### Network & WiFi (5 endpoints)
```
GET  /wifiscan.json            → Available WiFi networks
GET  /generate_204*            → Captive portal (Apple/Android) [NO AUTH]
GET  /hotspot-detect.html      → Apple captive portal [NO AUTH]
GET  /connecttest.txt          → Android captive portal [NO AUTH]
GET  /ncsi.txt                 → Windows captive portal [NO AUTH]
GET  /redirect                 → Portal redirect [NO AUTH]
```

### Mesh Nodes (3 endpoints)
```
GET  /nodes.json               → List all nodes
GET  /node_data.json           → Get node electrical data (requires node_id)
GET  /node_metrics.json        → Get node metrics (requires node_id)
```

### Current Transformer (3 endpoints)
```
GET  /ct.json                  → Latest clamp data (requires node_id)
GET  /ct_data.json             → Versioned clamp data (requires node_id)
GET  /ct_history.json          → Clamp history (requires node_id)
```

### Energy Management (5 endpoints)
```
GET  /ems.json                 → EMS status (battery, solar, grid)
GET  /ems_history.json         → Historical EMS data
GET  /ems_pid_history.json     → PID controller debug data
GET  /schedule.json            → Charging schedule
GET  /pid.json                 → PID controller state
```

### Hub & System (2 endpoints)
```
GET  /efr_hub_status.json      → Hub operational status
GET  /ecu_sense.json           → Sensor function assignments
```

### Error Management (2 endpoints)
```
GET  /error_report.json        → Current active errors
GET  /error_history.json       → Historical error log
```

### OTA Updates (2 endpoints)
```
GET  /ota_manifest.json        → Available updates & progress
POST /update                   → Upload firmware binary
```

### File Management (3 endpoints)
```
GET  /spiffs/{filepath}        → Download file
POST /upload/spiffs/{filepath} → Upload file
POST /delete/spiffs/{filepath} → Delete file
```

### Debugging (2 endpoints)
```
POST /console.json             → Execute CLI command
GET  /mains_data.json          → Mains voltage/frequency
```

### Network Testing (1 endpoint)
```
GET  /warp_ping.json           → Mesh network ping stats
```

**Total: 37 API endpoints**

---

## Common Query Parameters

| Parameter | Endpoints | Type | Description |
|-----------|-----------|------|-------------|
| `node_id` | Node endpoints | int | Mesh node identifier |
| `limit` | History endpoints | int | Max entries to return |
| `from` | History endpoints | int | Start timestamp (Unix) |
| `to` | History endpoints | int | End timestamp (Unix) |
| `level` | /logs.json | string | Log level filter |
| `timestamp` | /mains_data.json | int | Specific timestamp query |
| `severity` | /error_history.json | string | Error severity filter |

---

## Common Request/Response Patterns

### Typical GET Request
```bash
curl -u admin:<password> http://homevolt-<deviceid>.local/ems.json
```

### Typical POST Request (Form Data)
```bash
curl -u admin:<password> -X POST \
  -d "k=param_name&v=param_value&store=1" \
  http://homevolt-<deviceid>.local/params.json
```

### Typical POST Request (File Upload)
```bash
curl -u admin:<password> -X POST \
  --data-binary @firmware.bin \
  http://homevolt-<deviceid>.local/update
```

### Filter Query Parameters
```bash
curl -u admin:<password> "http://homevolt-<deviceid>.local/logs.json?limit=50&level=ERROR"
```

---

## Authentication

All endpoints (except captive portal) require:
```
Username: admin
Password: <QR-CODE-PASSWORD>
```

Use HTTP Basic Auth:
```bash
curl -u admin:<password> http://homevolt-<deviceid>.local/path
```

---

## Rate Limiting on Auth Failures

| Attempt | Lockout Duration | Status |
|---------|------------------|--------|
| 1-4 | None | Increments counter |
| 5 | 1 second | Account locked |
| 6 | 2 seconds | Account locked |
| 7 | 4 seconds | Account locked |
| 8+ | 10 seconds | Account locked (max) |

Counter resets after 5 minutes of inactivity.

---

## Response Codes

| Code | Status | When |
|------|--------|------|
| 200 | OK | Success |
| 204 | No Content | Success, empty response |
| 400 | Bad Request | Invalid parameters |
| 401 | Unauthorized | Wrong credentials |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 500 | Server Error | Internal error |
| 507 | Insufficient Storage | Device storage full |

---

## JSON Response Structures

### Battery/Power Data
```json
{
  "voltage": 48.2,
  "current": 25.5,
  "power": 1224,
  "soc": 75.0,
  "timestamp": 1703079600
}
```

### Node Info
```json
{
  "node_id": 1,
  "node_type": "CLAMP",
  "signal_strength": -65,
  "battery_percent": 87.5,
  "fw_version": "1.2.3"
}
```

### Error Report
```json
{
  "subsystem": "BATTERY",
  "error_code": 5,
  "severity": "WARNING",
  "description": "Over-temperature"
}
```

---

## Useful Command Combinations

### Monitor Real-Time Power
```bash
watch -n 2 'curl -s -u admin:<password> http://homevolt-<deviceid>.local/ems.json | jq ".grid_power"'
```

### Get Battery SOC Only
```bash
curl -s -u admin:<password> http://homevolt-<deviceid>.local/ems.json | jq '.battery_soc'
```

### List All Nodes and Signal Strength
```bash
curl -s -u admin:<password> http://homevolt-<deviceid>.local/nodes.json | jq '.[] | {id: .node_id, signal: .signal_strength}'
```

### Check for Critical Errors
```bash
curl -s -u admin:<password> http://homevolt-<deviceid>.local/error_report.json | jq '.errors[] | select(.severity=="CRITICAL")'
```

### Download All Logs
```bash
curl -u admin:<password> "http://homevolt-<deviceid>.local/logs.json?limit=10000" > logs.json
```

### Execute System Diagnostic
```bash
curl -s -u admin:<password> -X POST -d "cmd=status" http://homevolt-<deviceid>.local/console.json | jq '.output'
```

---

## Endpoint Availability

All endpoints are available on:
- HTTP: `http://homevolt-<deviceid>.local` (port 80)
- HTTPS: `https://homevolt-<deviceid>.local` (port 443, if enabled)
- IP Address: `http://<device-ip>`

Hostname defaults to `homevolt-<deviceid>.local` but can be configured.

---

## Rate Limiting Notes

- **Password attempts**: Protected with exponential backoff
- **API calls**: Generally unlimited for authenticated users
- **File operations**: May be slower with large files
- **History queries**: Performance depends on amount of stored data

---

## Security Best Practices

1. ✅ Use HTTPS in production
2. ✅ Change default password immediately
3. ✅ Use strong passwords (12+ characters)
4. ✅ Monitor auth failures in logs
5. ✅ Keep firmware updated
6. ✅ Restrict network access to trusted devices
7. ✅ Use firewall rules for internet-facing deployments
8. ✅ Regularly review error logs

---

## Timestamp Format

All timestamps use **Unix epoch** (seconds since 1970-01-01 00:00:00 UTC).

Convert to readable format:
```bash
# Linux/macOS
date -r 1703079600

# Python
python3 -c "from datetime import datetime; print(datetime.fromtimestamp(1703079600))"

# JavaScript
new Date(1703079600 * 1000).toISOString()
```

---

## Power Sign Conventions

| Value | Sign | Meaning |
|-------|------|---------|
| Battery Power | + | Discharging |
| Battery Power | - | Charging |
| Grid Power | + | Importing (consuming) |
| Grid Power | - | Exporting (feeding back) |
| Solar Power | Always + | Generating |
| Load Power | Always + | Consuming |
| Inverter Power | Always + | Generating |

---

## Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| 401 errors | Wrong password | Check QR code on device |
| Node not appearing | Out of range | Move closer to hub |
| High packet loss | WiFi interference | Change channel or location |
| 503 errors | System busy | Wait 30 seconds and retry |
| Slow responses | Many history entries | Reduce `limit` parameter |

---

## Documentation Files

- **API_DOCUMENTATION.yaml** - Full OpenAPI/Swagger specification
- **API_DOCUMENTATION.md** - Human-readable detailed documentation
- **API_QUICK_REFERENCE.md** - This file

Use the Swagger/OpenAPI file with tools like:
- [Swagger UI](https://swagger.io/tools/swagger-ui/)
- [Postman](https://www.postman.com/)
- [ReDoc](https://redoc.ly/)
- Any OpenAPI-compatible client
