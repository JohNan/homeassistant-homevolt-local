"""The Homevolt Local integration."""

from __future__ import annotations

import logging
from datetime import timedelta

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    Platform,
)
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import async_get as async_get_device_registry
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

from .const import (
    CONF_HOST,
    CONF_HOSTS,
    CONF_MAIN_HOST,
    CONF_RESOURCE,
    CONF_RESOURCES,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
    EMS_RESOURCE_PATH,
)
from .coordinator import HomevoltDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

# Null euid used by virtual/calculated sensors (like load)
NULL_EUID = "0000000000000000"

# Sensor types that may have null euid
VIRTUAL_SENSOR_TYPES = ["load", "grid", "solar"]

# Sensor keys that need migration (sensor_specific sensors)
SENSOR_KEYS_TO_MIGRATE = [
    "grid_power",
    "grid_energy_imported",
    "grid_energy_exported",
    "grid_rssi",
    "grid_pdr",
    "solar_power",
    "solar_energy_imported",
    "solar_energy_exported",
    "solar_rssi",
    "solar_pdr",
    "load_power",
    "load_energy_imported",
    "load_energy_exported",
]


def _migrate_sensor_unique_ids(
    hass: HomeAssistant, entry: ConfigEntry, main_device_id: str
) -> None:
    """Migrate sensor unique IDs from old format to new format.

    Old format: homevolt_local_{key}_sensor_{euid}
    New format: homevolt_local_{key}_{main_id}_{sensor_type}

    This migration is needed for sensors with null euid (0000000000000000).
    """
    entity_registry = async_get_entity_registry(hass)

    for entity_entry in list(entity_registry.entities.values()):
        if entity_entry.config_entry_id != entry.entry_id:
            continue

        if entity_entry.platform != DOMAIN:
            continue

        # Check if this is an old format unique ID with null euid
        old_suffix = f"_sensor_{NULL_EUID}"
        if not entity_entry.unique_id.endswith(old_suffix):
            continue

        # Extract the key from the old unique ID
        # Format: homevolt_local_{key}_sensor_{euid}
        prefix = f"{DOMAIN}_"
        if not entity_entry.unique_id.startswith(prefix):
            continue

        # Get the key part (between prefix and _sensor_)
        remainder = entity_entry.unique_id[len(prefix) :]
        if "_sensor_" not in remainder:
            continue

        key = remainder.split("_sensor_")[0]

        # Determine sensor type from key
        sensor_type = None
        for st in VIRTUAL_SENSOR_TYPES:
            if key.startswith(f"{st}_"):
                sensor_type = st
                break

        if not sensor_type:
            continue

        # Build new unique ID
        new_unique_id = f"{DOMAIN}_{key}_{main_device_id}_{sensor_type}"

        # Check if new unique ID already exists
        if entity_registry.async_get_entity_id(Platform.SENSOR, DOMAIN, new_unique_id):
            _LOGGER.debug(
                "Cannot migrate %s: new unique ID %s already exists",
                entity_entry.entity_id,
                new_unique_id,
            )
            continue

        _LOGGER.info(
            "Migrating entity %s unique ID from %s to %s",
            entity_entry.entity_id,
            entity_entry.unique_id,
            new_unique_id,
        )

        entity_registry.async_update_entity(
            entity_entry.entity_id, new_unique_id=new_unique_id
        )


def _get_main_device_id(
    coordinator: HomevoltDataUpdateCoordinator,
    ecu_id: int | None,
    entry_id: str,
) -> str:
    """Get the main device identifier for unique ID generation.

    Uses ecu_id from config or data, with fallback to entry_id.
    """
    # First try to use ecu_id from config
    if ecu_id:
        return str(ecu_id)
    # Then try to get it from the coordinator data
    if coordinator.data and coordinator.data.ems:
        try:
            first_ems = coordinator.data.ems[0]
            if first_ems.ecu_id:
                return str(first_ems.ecu_id)
        except (IndexError, AttributeError):
            pass
    # Fallback to entry_id
    return entry_id


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Homevolt Local from a config entry."""
    # Handle both old and new config entry formats
    if CONF_RESOURCES in entry.data:
        # New format with multiple resources
        resources = entry.data[CONF_RESOURCES]
        hosts = entry.data[CONF_HOSTS]
        main_host = entry.data[CONF_MAIN_HOST]
    else:
        # Old format with a single resource
        resources = [entry.data[CONF_RESOURCE]]

        # Extract host from resource URL if CONF_HOST is not available
        if CONF_HOST in entry.data:
            hosts = [entry.data[CONF_HOST]]
        else:
            # Extract host from resource URL
            resource_url = entry.data[CONF_RESOURCE]
            try:
                # Remove protocol and path
                if "://" in resource_url:
                    host = resource_url.split("://")[1].split("/")[0]
                else:
                    host = resource_url.split("/")[0]
                hosts = [host]
            except (IndexError, ValueError):
                hosts = ["unknown"]

        main_host = hosts[0]

    username = (entry.data.get(CONF_USERNAME) or "").strip() or None
    password = (entry.data.get(CONF_PASSWORD) or "").strip() or None
    verify_ssl = entry.data.get(CONF_VERIFY_SSL, True)
    scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    # Cap timeout at DEFAULT_TIMEOUT (migration for old entries with high timeout)
    stored_timeout = entry.data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
    timeout = min(stored_timeout, DEFAULT_TIMEOUT)
    # Get stored ecu_id for stable device identification
    ecu_id = entry.data.get("ecu_id")

    session = async_get_clientsession(hass, verify_ssl=verify_ssl)

    coordinator = HomevoltDataUpdateCoordinator(
        hass,
        _LOGGER,
        entry_id=entry.entry_id,
        resources=resources,
        hosts=hosts,
        main_host=main_host,
        ecu_id=ecu_id,
        username=username,
        password=password,
        session=session,
        update_interval=timedelta(seconds=scan_interval),
        timeout=timeout,
    )

    await coordinator.async_config_entry_first_refresh()

    # Migrate sensor unique IDs for sensors with null euid
    # This must be done after coordinator has data but before entities are set up
    main_device_id = _get_main_device_id(coordinator, ecu_id, entry.entry_id)
    _migrate_sensor_unique_ids(hass, entry, main_device_id)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def async_add_schedule(call: ServiceCall) -> None:
        """Handle the service call to add a schedule."""
        device_registry = async_get_device_registry(hass)
        device_ids = call.data.get("device_id")

        if not device_ids:
            _LOGGER.error("No device_id provided")
            return

        # Ensure device_ids is a list
        if not isinstance(device_ids, list):
            device_ids = [device_ids]

        for device_id in device_ids:
            device_entry = device_registry.async_get(device_id)
            if not device_entry:
                _LOGGER.error("Device not found: %s", device_id)
                continue

            # Find the config entry associated with this device
            config_entry_id = next(iter(device_entry.config_entries), None)
            if not config_entry_id:
                _LOGGER.error(
                    "Device %s is not associated with a config entry", device_id
                )
                continue

            config_entry = hass.config_entries.async_get_entry(config_entry_id)
            if not config_entry:
                _LOGGER.error("Config entry not found for device %s", device_id)
                continue

            # Extract connection details from the config entry
            host = config_entry.data.get(CONF_MAIN_HOST)
            username = (config_entry.data.get(CONF_USERNAME) or "").strip() or None
            password = (config_entry.data.get(CONF_PASSWORD) or "").strip() or None
            verify_ssl = config_entry.data.get(CONF_VERIFY_SSL, True)

            if not host:
                _LOGGER.error("No host found for device %s", device_id)
                continue

            mode = call.data["mode"]
            setpoint = call.data["setpoint"]
            from_time = call.data["from_time"].strftime("%Y-%m-%dT%H:%M:%S")
            to_time = call.data["to_time"].strftime("%Y-%m-%dT%H:%M:%S")

            command = (
                f"sched_add {mode} --setpoint {setpoint} "
                f"--from={from_time} --to={to_time}"
            )
            url = f"{host}{EMS_RESOURCE_PATH}"

            try:
                session = async_get_clientsession(hass, verify_ssl=verify_ssl)
                form_data = aiohttp.FormData()
                form_data.add_field("cmd", command)

                auth = (
                    aiohttp.BasicAuth(username, password)
                    if username and password
                    else None
                )

                async with session.post(url, data=form_data, auth=auth) as response:
                    response_text = await response.text()
                    if response.status == 200:
                        _LOGGER.info(
                            "Successfully sent command to %s: %s", host, command
                        )
                    else:
                        _LOGGER.error(
                            "Failed to send command to %s. Status: %s, Response: %s",
                            host,
                            response.status,
                            response_text,
                        )
            except aiohttp.ClientError as e:
                _LOGGER.error("Error sending command to %s: %s", host, e)

    hass.services.async_register(DOMAIN, "add_schedule", async_add_schedule)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
