"""Switch platform for Homevolt Local integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import HomevoltDataUpdateCoordinator
from .entity import HomevoltEntity

_LOGGER = logging.getLogger(__name__)

SWITCH_DESCRIPTION = SwitchEntityDescription(
    key="local_mode",
    translation_key="local_mode",
    icon="mdi:shield-home",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Homevolt Local switch entities."""
    coordinator: HomevoltDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([HomevoltLocalModeSwitch(coordinator, SWITCH_DESCRIPTION)])


class HomevoltLocalModeSwitch(HomevoltEntity, SwitchEntity):
    """Switch to enable/disable local mode on the Homevolt device."""

    entity_description: SwitchEntityDescription

    def __init__(
        self,
        coordinator: HomevoltDataUpdateCoordinator,
        description: SwitchEntityDescription,
    ) -> None:
        """Initialize the switch entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{DOMAIN}_{description.key}_{coordinator.get_main_device_id()}"
        )

    @property
    def is_on(self) -> bool:
        """Return true if local mode is on."""
        if self.coordinator.data:
            return bool(self.coordinator.data.local_mode)
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on local mode."""
        await self.coordinator.async_set_local_mode(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off local mode."""
        await self.coordinator.async_set_local_mode(False)
