"""The Homevolt Local integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

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
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service import async_extract_config_entry_ids

from .const import (
    CONF_HOST,
    CONF_HOSTS,
    CONF_MAIN_HOST,
    CONF_RESOURCE,
    CONF_RESOURCES,
    CONSOLE_RESOURCE_PATH,
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_READ_TIMEOUT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import HomevoltDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]

# Null euid used by virtual/calculated sensors (like load)
NULL_EUID = "0000000000000000"

# Sensor types that may have null euid
VIRTUAL_SENSOR_TYPES = ["load", "grid", "solar"]


async def _async_migrate_sensor_unique_ids(
    hass: HomeAssistant, entry: ConfigEntry, main_device_id: str
) -> None:
    """Migrate sensor unique IDs from old format to new format.

    Old format: homevolt_local_{key}_sensor_{euid}
    New format: homevolt_local_{key}_{main_id}_{sensor_type}

    This migration is needed for sensors with null euid (0000000000000000).
    """
    entity_registry = er.async_get(hass)

    @callback
    def _async_migrator(entity_entry: er.RegistryEntry) -> dict[str, Any] | None:
        """Migrate a single entity's unique ID if needed."""
        # Check if this is an old format unique ID with null euid
        old_suffix = f"_sensor_{NULL_EUID}"
        if not entity_entry.unique_id.endswith(old_suffix):
            return None

        # Extract the key from the old unique ID
        # Format: homevolt_local_{key}_sensor_{euid}
        prefix = f"{DOMAIN}_"
        if not entity_entry.unique_id.startswith(prefix):
            return None

        # Get the key part (between prefix and _sensor_)
        remainder = entity_entry.unique_id[len(prefix) :]
        if "_sensor_" not in remainder:
            return None

        key = remainder.split("_sensor_")[0]

        # Determine sensor type from key
        sensor_type = None
        for st in VIRTUAL_SENSOR_TYPES:
            if key.startswith(f"{st}_"):
                sensor_type = st
                break

        if not sensor_type:
            _LOGGER.warning(
                "Sensor %s has null EUID but key '%s' doesn't match any known "
                "virtual sensor type (%s) - skipping migration",
                entity_entry.entity_id,
                key,
                ", ".join(VIRTUAL_SENSOR_TYPES),
            )
            return None

        # Build new unique ID
        new_unique_id = f"{DOMAIN}_{key}_{main_device_id}_{sensor_type}"

        # Check if new unique ID already exists
        if entity_registry.async_get_entity_id(Platform.SENSOR, DOMAIN, new_unique_id):
            _LOGGER.debug(
                "Cannot migrate %s: new unique ID %s already exists",
                entity_entry.entity_id,
                new_unique_id,
            )
            return None

        _LOGGER.info(
            "Migrating entity %s unique ID from %s to %s",
            entity_entry.entity_id,
            entity_entry.unique_id,
            new_unique_id,
        )

        return {"new_unique_id": new_unique_id}

    await er.async_migrate_entries(hass, entry.entry_id, _async_migrator)


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
    read_timeout = entry.data.get(CONF_TIMEOUT, DEFAULT_READ_TIMEOUT)
    # Get stored ecu_id for stable device identification
    ecu_id = entry.data.get("ecu_id")

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
        verify_ssl=verify_ssl,
        update_interval=timedelta(seconds=scan_interval),
        read_timeout=read_timeout,
    )

    await coordinator.async_config_entry_first_refresh()

    # Migrate sensor unique IDs for sensors with null euid
    # This must be done after coordinator has data but before entities are set up
    await _async_migrate_sensor_unique_ids(
        hass, entry, coordinator.get_main_device_id()
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def async_add_schedule(call: ServiceCall) -> None:
        """Handle the service call to add a schedule."""
        try:
            config_entry_ids = await async_extract_config_entry_ids(call)
        except Exception as e:
            _LOGGER.error("Failed to extract config entries: %s", e)
            return

        if not config_entry_ids:
            _LOGGER.error("No config entries found for target")
            return

        for config_entry_id in config_entry_ids:
            config_entry = hass.config_entries.async_get_entry(config_entry_id)
            if not config_entry:
                _LOGGER.error("Config entry not found: %s", config_entry_id)
                continue

            # Extract connection details from the config entry
            host = config_entry.data.get(CONF_MAIN_HOST)
            username = (config_entry.data.get(CONF_USERNAME) or "").strip() or None
            password = (config_entry.data.get(CONF_PASSWORD) or "").strip() or None
            verify_ssl = config_entry.data.get(CONF_VERIFY_SSL, True)
            read_timeout = config_entry.data.get(CONF_TIMEOUT, DEFAULT_READ_TIMEOUT)

            if not host:
                _LOGGER.error("No host found for config entry %s", config_entry_id)
                continue

            mode = call.data["mode"]
            from_time = call.data["from_time"]
            to_time = call.data["to_time"]

            if hasattr(from_time, "strftime"):
                from_time = from_time.strftime("%Y-%m-%dT%H:%M:%S")
            elif isinstance(from_time, str):
                from_time = from_time.replace(" ", "T")

            if hasattr(to_time, "strftime"):
                to_time = to_time.strftime("%Y-%m-%dT%H:%M:%S")
            elif isinstance(to_time, str):
                to_time = to_time.replace(" ", "T")

            command_parts = [f"sched_add {mode}"]

            if from_time:
                command_parts.append(f"--from={from_time}")
            if to_time:
                command_parts.append(f"--to={to_time}")
            if "setpoint" in call.data:
                command_parts.append(f"-s {call.data['setpoint']}")
            if "max_charge" in call.data:
                command_parts.append(f"-c {call.data['max_charge']}")
            if "max_discharge" in call.data:
                command_parts.append(f"-d {call.data['max_discharge']}")
            if "min_soc" in call.data:
                command_parts.append(f"--min {call.data['min_soc']}")
            if "max_soc" in call.data:
                command_parts.append(f"--max {call.data['max_soc']}")

            command = " ".join(command_parts)
            url = f"{host}{CONSOLE_RESOURCE_PATH}"

            try:
                auth = (
                    aiohttp.BasicAuth(username, password)
                    if username and password
                    else None
                )
                timeout = aiohttp.ClientTimeout(
                    connect=DEFAULT_CONNECT_TIMEOUT, sock_read=read_timeout
                )
                session = async_get_clientsession(hass, verify_ssl=verify_ssl)
                async with session.post(
                    url, data={"cmd": command}, auth=auth, timeout=timeout
                ) as response:
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
            except TimeoutError:
                _LOGGER.error("Timeout sending command to %s", host)
            except aiohttp.ClientError as e:
                _LOGGER.error("Error sending command to %s: %s", host, e)

    async def async_delete_schedule(call: ServiceCall) -> None:
        """Handle the service call to delete a schedule."""
        try:
            config_entry_ids = await async_extract_config_entry_ids(call)
        except Exception as e:
            _LOGGER.error("Failed to extract config entries: %s", e)
            return

        if not config_entry_ids:
            _LOGGER.error("No config entries found for target")
            return

        schedule_id = call.data["schedule_id"]
        command = f"sched_del {schedule_id}"

        for config_entry_id in config_entry_ids:
            config_entry = hass.config_entries.async_get_entry(config_entry_id)
            if not config_entry:
                _LOGGER.error("Config entry not found: %s", config_entry_id)
                continue

            # Extract connection details from the config entry
            host = config_entry.data.get(CONF_MAIN_HOST)
            username = (config_entry.data.get(CONF_USERNAME) or "").strip() or None
            password = (config_entry.data.get(CONF_PASSWORD) or "").strip() or None
            verify_ssl = config_entry.data.get(CONF_VERIFY_SSL, True)
            read_timeout = config_entry.data.get(CONF_TIMEOUT, DEFAULT_READ_TIMEOUT)

            if not host:
                _LOGGER.error("No host found for config entry %s", config_entry_id)
                continue

            url = f"{host}{CONSOLE_RESOURCE_PATH}"

            try:
                auth = (
                    aiohttp.BasicAuth(username, password)
                    if username and password
                    else None
                )
                timeout = aiohttp.ClientTimeout(
                    connect=DEFAULT_CONNECT_TIMEOUT, sock_read=read_timeout
                )
                session = async_get_clientsession(hass, verify_ssl=verify_ssl)
                async with session.post(
                    url, data={"cmd": command}, auth=auth, timeout=timeout
                ) as response:
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
            except TimeoutError:
                _LOGGER.error("Timeout sending command to %s", host)
            except aiohttp.ClientError as e:
                _LOGGER.error("Error sending command to %s: %s", host, e)

    hass.services.async_register(DOMAIN, "add_schedule", async_add_schedule)
    hass.services.async_register(DOMAIN, "delete_schedule", async_delete_schedule)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
