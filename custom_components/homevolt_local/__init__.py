"""The Homevolt Local integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

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
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_HOST,
    CONF_HOSTS,
    CONF_MAIN_HOST,
    CONF_RESOURCE,
    CONF_RESOURCES,
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


def _format_time(val: Any) -> str:
    """Format datetime or string to ISO datetime format."""
    if hasattr(val, "strftime"):
        return val.strftime("%Y-%m-%dT%H:%M:%S")
    return str(val)


def _build_schedule_command(cmd_name: str, data: dict[str, Any]) -> str:
    """Build a console command string for sched_set or sched_add."""
    mode = data.get("mode")
    parts = [f"{cmd_name} {mode}"]

    if "from_time" in data and data["from_time"] is not None:
        parts.append(f"--from {_format_time(data['from_time'])}")

    if "to_time" in data and data["to_time"] is not None:
        parts.append(f"--to {_format_time(data['to_time'])}")

    if "setpoint" in data and data["setpoint"] is not None:
        parts.append(f"-s {data['setpoint']}")

    if "max_charge" in data and data["max_charge"] is not None:
        parts.append(f"-c {data['max_charge']}")

    if "max_discharge" in data and data["max_discharge"] is not None:
        parts.append(f"-d {data['max_discharge']}")

    if "min_soc" in data and data["min_soc"] is not None:
        parts.append(f"--min {data['min_soc']}")

    if "max_soc" in data and data["max_soc"] is not None:
        parts.append(f"--max {data['max_soc']}")

    if "import_limit" in data and data["import_limit"] is not None:
        parts.append(f"-l {data['import_limit']}")

    if "export_limit" in data and data["export_limit"] is not None:
        parts.append(f"-x {data['export_limit']}")

    if data.get("offline") is True:
        parts.append("-o")

    return " ".join(parts)


def _get_coordinators_for_service_call(
    hass: HomeAssistant, call: ServiceCall
) -> list[HomevoltDataUpdateCoordinator]:
    """Extract coordinators from service call targets."""
    domain_data = hass.data.get(DOMAIN, {})
    if not domain_data:
        _LOGGER.error("No Homevolt Local integrations found")
        return []

    coordinators: list[HomevoltDataUpdateCoordinator] = []

    # Extract target device_ids
    target_device_ids = call.data.get("device_id", [])
    if isinstance(target_device_ids, str):
        target_device_ids = [target_device_ids]
    elif not isinstance(target_device_ids, list):
        target_device_ids = list(target_device_ids)
    else:
        target_device_ids = list(target_device_ids)

    # Extract target entity_ids
    target_entity_ids = call.data.get("entity_id", [])
    if isinstance(target_entity_ids, str):
        target_entity_ids = [target_entity_ids]
    elif not isinstance(target_entity_ids, list):
        target_entity_ids = list(target_entity_ids)

    # Map entity_ids to config_entries / device_ids
    if target_entity_ids:
        entity_reg = er.async_get(hass)
        for entity_id in target_entity_ids:
            ent = entity_reg.async_get(entity_id)
            if ent:
                if ent.config_entry_id and ent.config_entry_id in domain_data:
                    coord = domain_data[ent.config_entry_id]
                    if coord not in coordinators:
                        coordinators.append(coord)
                elif ent.device_id and ent.device_id not in target_device_ids:
                    target_device_ids.append(ent.device_id)

    # Map device_ids to coordinators
    if target_device_ids:
        device_reg = dr.async_get(hass)
        for dev_id in target_device_ids:
            dev = device_reg.async_get(dev_id)
            if dev:
                for entry_id in dev.config_entries:
                    if entry_id in domain_data:
                        coord = domain_data[entry_id]
                        if coord not in coordinators:
                            coordinators.append(coord)

    # If no specific target was found, apply to all loaded coordinators
    if (
        not coordinators
        and not call.data.get("device_id")
        and not call.data.get("entity_id")
    ):
        coordinators = list(domain_data.values())

    return coordinators


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

    async def async_handle_add_schedule(call: ServiceCall) -> None:
        """Handle adding a schedule entry."""
        coordinators = _get_coordinators_for_service_call(hass, call)
        if not coordinators:
            _LOGGER.error("No Homevolt coordinator found for add_schedule call")
            return

        command = _build_schedule_command("sched_add", call.data)
        for coord in coordinators:
            try:
                await coord.async_execute_command(command)
                await coord.async_request_refresh()
            except Exception as err:
                _LOGGER.error(
                    "Failed to execute '%s' on %s: %s", command, coord.main_host, err
                )

    async def async_handle_set_schedule(call: ServiceCall) -> None:
        """Handle setting/replacing immediate battery schedule."""
        coordinators = _get_coordinators_for_service_call(hass, call)
        if not coordinators:
            _LOGGER.error("No Homevolt coordinator found for set_schedule call")
            return

        command = _build_schedule_command("sched_set", call.data)
        for coord in coordinators:
            try:
                await coord.async_execute_command(command)
                await coord.async_request_refresh()
            except Exception as err:
                _LOGGER.error(
                    "Failed to execute '%s' on %s: %s", command, coord.main_host, err
                )

    async def async_handle_delete_schedule(call: ServiceCall) -> None:
        """Handle deleting a schedule entry by ID."""
        coordinators = _get_coordinators_for_service_call(hass, call)
        if not coordinators:
            _LOGGER.error("No Homevolt coordinator found for delete_schedule call")
            return

        schedule_id = call.data.get("schedule_id")
        command = f"sched_del {schedule_id}"
        for coord in coordinators:
            try:
                await coord.async_execute_command(command)
                await coord.async_request_refresh()
            except Exception as err:
                _LOGGER.error(
                    "Failed to execute '%s' on %s: %s", command, coord.main_host, err
                )

    async def async_handle_clear_schedules(call: ServiceCall) -> None:
        """Handle clearing all schedules."""
        coordinators = _get_coordinators_for_service_call(hass, call)
        if not coordinators:
            _LOGGER.error("No Homevolt coordinator found for clear_schedules call")
            return

        command = "sched_clear"
        for coord in coordinators:
            try:
                await coord.async_execute_command(command)
                await coord.async_request_refresh()
            except Exception as err:
                _LOGGER.error(
                    "Failed to execute '%s' on %s: %s", command, coord.main_host, err
                )

    if not hass.services.has_service(DOMAIN, "add_schedule"):
        hass.services.async_register(DOMAIN, "add_schedule", async_handle_add_schedule)
    if not hass.services.has_service(DOMAIN, "set_schedule"):
        hass.services.async_register(DOMAIN, "set_schedule", async_handle_set_schedule)
    if not hass.services.has_service(DOMAIN, "delete_schedule"):
        hass.services.async_register(
            DOMAIN, "delete_schedule", async_handle_delete_schedule
        )
    if not hass.services.has_service(DOMAIN, "clear_schedules"):
        hass.services.async_register(
            DOMAIN, "clear_schedules", async_handle_clear_schedules
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            for svc in (
                "add_schedule",
                "set_schedule",
                "delete_schedule",
                "clear_schedules",
            ):
                hass.services.async_remove(DOMAIN, svc)

    return unload_ok
