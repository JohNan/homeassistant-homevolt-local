"""Constants for the Homevolt Local integration."""

DOMAIN = "homevolt_local"

# Configuration constants
CONF_RESOURCE = "resource"
CONF_HOST = "host"
CONF_HOSTS = "hosts"
CONF_MAIN_HOST = "main_host"
CONF_RESOURCES = "resources"
CONF_ADD_ANOTHER = "add_another"
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_TIMEOUT = 30
EMS_RESOURCE_PATH = "/ems.json"
CONSOLE_RESOURCE_PATH = "/console.json"

# Attribute keys from the API response
ATTR_EMS = "ems"
ATTR_AGGREGATED = "aggregated"
ATTR_SENSORS = "sensors"
ATTR_EMS_DATA = "ems_data"
ATTR_STATE_STR = "state_str"
ATTR_SOC_AVG = "soc_avg"
ATTR_ERROR_STR = "error_str"
ATTR_POWER = "power"
ATTR_ENERGY_PRODUCED = "energy_produced"
ATTR_ENERGY_CONSUMED = "energy_consumed"

# Device identification attributes
ATTR_ECU_ID = "ecu_id"
ATTR_SERIAL_NUMBER = "serial_number"
ATTR_FW_VERSION = "fw_version"
ATTR_INV_INFO = "inv_info"
ATTR_BMS_INFO = "bms_info"
ATTR_EMS_INFO = "ems_info"

# Sensor data attributes
ATTR_TOTAL_POWER = "total_power"
ATTR_ENERGY_IMPORTED = "energy_imported"
ATTR_ENERGY_EXPORTED = "energy_exported"
ATTR_PHASE = "phase"

# Sensor identification attributes
ATTR_TYPE = "type"
ATTR_NODE_ID = "node_id"
ATTR_EUID = "euid"
ATTR_AVAILABLE = "available"
ATTR_TIMESTAMP = "timestamp"

# Sensor types
SENSOR_TYPE_GRID = "grid"
SENSOR_TYPE_SOLAR = "solar"
SENSOR_TYPE_LOAD = "load"

# Sensor indices
SENSOR_INDEX_GRID = 0
SENSOR_INDEX_SOLAR = 1
SENSOR_INDEX_LOAD = 2

# BMS data indices
BMS_DATA_INDEX_DEVICE = 0
BMS_DATA_INDEX_TOTAL = 1
