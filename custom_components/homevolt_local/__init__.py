"""The Homevolt Local integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional, Union

import aiohttp
import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    ATTR_AGGREGATED,
    ATTR_ECU_ID,
    ATTR_EMS,
    ATTR_EUID,
    ATTR_SENSORS,
    CONF_HOST,
    CONF_HOSTS,
    CONF_MAIN_HOST,
    CONF_RESOURCE,
    CONF_RESOURCES,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
)
from .models import HomevoltData

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


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
    timeout = entry.data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)

    session = async_get_clientsession(hass, verify_ssl=verify_ssl)

    coordinator = HomevoltDataUpdateCoordinator(
        hass,
        _LOGGER,
        entry_id=entry.entry_id,
        resources=resources,
        hosts=hosts,
        main_host=main_host,
        username=username,
        password=password,
        session=session,
        update_interval=timedelta(seconds=scan_interval),
        timeout=timeout,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class HomevoltDataUpdateCoordinator(DataUpdateCoordinator[Union[HomevoltData, Dict[str, Any]]]):
    """Class to manage fetching Homevolt data."""

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger,
        entry_id: str,
        resources: List[str],
        hosts: List[str],
        main_host: str,
        username: Optional[str],
        password: Optional[str],
        session: aiohttp.ClientSession,
        update_interval: timedelta,
        timeout: int,
    ) -> None:
        """Initialize."""
        self.entry_id = entry_id
        self.resources = resources
        self.hosts = hosts
        self.main_host = main_host
        self.username = username
        self.password = password
        self.session = session
        self.timeout = timeout

        # For backward compatibility
        self.resource = resources[0] if resources else ""

        super().__init__(hass, logger, name=DOMAIN, update_interval=update_interval)

    async def _fetch_resource_data(self, resource: str) -> Dict[str, Any]:
        """Fetch data from a single resource."""
        try:
            async with async_timeout.timeout(self.timeout):
                # Only use authentication if both username and password are provided
                auth = None
                if self.username and self.password:
                    auth = aiohttp.BasicAuth(self.username, self.password)
                
                async with self.session.get(resource, auth=auth) as resp:
                    if resp.status != 200:
                        raise UpdateFailed(f"Error communicating with API: {resp.status}")
                    return await resp.json()
        except asyncio.TimeoutError as error:
            raise UpdateFailed(f"Timeout error fetching data from {resource}: {error}") from error
        except (aiohttp.ClientError, ValueError) as error:
            raise UpdateFailed(f"Error fetching data from {resource}: {error}") from error

    async def _async_update_data(self) -> HomevoltData:
        """Fetch data from all Homevolt API resources."""
        if not self.resources:
            raise UpdateFailed("No resources configured")

        # Fetch data from all resources in parallel
        tasks = [self._fetch_resource_data(resource) for resource in self.resources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process the results
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error("Error fetching data from %s: %s", self.resources[i], result)
            else:
                valid_results.append((self.hosts[i], result))

        if not valid_results:
            raise UpdateFailed("Failed to fetch data from any resource")

        # Find the main system's data
        main_data = None
        for host, data in valid_results:
            if host == self.main_host:
                main_data = data
                break

        # If main system's data is not available, use the first valid result
        if main_data is None:
            self.logger.warning("Main system data not available, using first valid result")
            main_data = valid_results[0][1]

        # Merge data from all systems
        merged_dict_data = self._merge_data(valid_results, main_data)

        # Convert the merged dictionary data to a HomevoltData object
        return HomevoltData.from_dict(merged_dict_data)

    def _merge_data(self, results: List[tuple[str, Dict[str, Any]]], main_data: Dict[str, Any]) -> Dict[str, Any]:
        """Merge data from multiple systems."""
        # Start with the main system's data
        merged_data = dict(main_data)

        # Collect all EMS devices and sensors from all systems
        all_ems = []
        all_sensors = []

        for _, data in results:
            # Add EMS devices
            if ATTR_EMS in data:
                for ems in data[ATTR_EMS]:
                    # Check if this EMS device is already in the list (based on ecu_id)
                    if ATTR_ECU_ID in ems:
                        ecu_id = ems[ATTR_ECU_ID]
                        if not any(e.get(ATTR_ECU_ID) == ecu_id for e in all_ems):
                            all_ems.append(ems)
                    else:
                        # If no ecu_id, just add it
                        all_ems.append(ems)

            # Add sensors
            if ATTR_SENSORS in data:
                for sensor in data[ATTR_SENSORS]:
                    # Check if this sensor is already in the list (based on euid)
                    if ATTR_EUID in sensor:
                        euid = sensor[ATTR_EUID]
                        if not any(s.get(ATTR_EUID) == euid for s in all_sensors):
                            all_sensors.append(sensor)
                    else:
                        # If no euid, just add it
                        all_sensors.append(sensor)

        # Update the merged data with all EMS devices and sensors
        merged_data[ATTR_EMS] = all_ems
        merged_data[ATTR_SENSORS] = all_sensors

        return merged_data
