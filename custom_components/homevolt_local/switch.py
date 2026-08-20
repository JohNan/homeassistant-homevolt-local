"""Switch platform for Homevolt Local."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONSOLE_RESOURCE_PATH,
    DEFAULT_CONNECT_TIMEOUT,
    DOMAIN,
)
from .coordinator import HomevoltDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Homevolt Local switch platform."""
    coordinator: HomevoltDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # We create a single switch for the main device to control local mode
    entities = [HomevoltLocalModeSwitch(coordinator)]
    async_add_entities(entities)


class HomevoltLocalModeSwitch(
    CoordinatorEntity[HomevoltDataUpdateCoordinator], SwitchEntity
):
    """Switch to enable/disable local mode."""

    def __init__(self, coordinator: HomevoltDataUpdateCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_local_mode_{coordinator.get_main_device_id()}"
        self._attr_name = f"Homevolt {coordinator.get_main_device_id()} Local Mode"
        self._attr_has_entity_name = True
        self.entity_id = (
            f"switch.{DOMAIN}_local_mode_{coordinator.get_main_device_id().lower()}"
        )
        # Device info ties this switch to the main device
        # Tie to the main device
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.get_main_device_id())},
            "name": "System",
        }

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        # Check if local mode is on in the parsed schedule data.
        # It's returned in the schedule fetch. We need to expose it in coordinator.
        if hasattr(self.coordinator.data, "local_mode"):
            return self.coordinator.data.local_mode
        # If not fetched yet or not in models, check raw dict
        return getattr(self.coordinator.data, "local_mode", None)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self._async_set_local_mode(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self._async_set_local_mode(False)

    async def _async_set_local_mode(self, enabled: bool) -> None:
        """Send the command to set local mode."""
        value = "1" if enabled else "0"
        command = f"param_set settings_local {value}"

        host = self.coordinator.main_host
        url = f"{host}{CONSOLE_RESOURCE_PATH}"

        try:
            auth = self.coordinator._auth
            timeout = aiohttp.ClientTimeout(
                connect=DEFAULT_CONNECT_TIMEOUT,
                sock_read=self.coordinator._read_timeout,
            )
            session = async_get_clientsession(
                self.hass, verify_ssl=self.coordinator._verify_ssl
            )
            async with session.post(
                url, data={"cmd": command}, auth=auth, timeout=timeout
            ) as response:
                if response.status == 200:
                    _LOGGER.info("Successfully set local mode to %s", enabled)
                    # Trigger a manual refresh to update state
                    await self.coordinator.async_request_refresh()
                else:
                    _LOGGER.error(
                        "Failed to set local mode. Status: %s", response.status
                    )
        except Exception as e:
            _LOGGER.error("Error setting local mode: %s", e)
