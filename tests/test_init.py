"""Tests for Homevolt Local integration setup."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.homevolt_local.const import DOMAIN

from .conftest import setup_integration


async def test_async_setup_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api_client: MagicMock,
) -> None:
    """Test a successful setup entry."""
    entry = await setup_integration(hass, mock_config_entry)

    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state is ConfigEntryState.LOADED

    # Verify coordinator is stored in hass.data
    assert DOMAIN in hass.data
    assert entry.entry_id in hass.data[DOMAIN]


async def test_async_setup_entry_and_unload(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api_client: MagicMock,
) -> None:
    """Test a successful setup and unload of entry."""
    entry = await setup_integration(hass, mock_config_entry)

    assert entry.state is ConfigEntryState.LOADED

    # Unload the entry
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert entry.entry_id not in hass.data.get(DOMAIN, {})


async def test_async_setup_entry_api_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test setup when API returns error."""
    from unittest.mock import AsyncMock

    with patch(
        "custom_components.homevolt_local.async_get_clientsession"
    ) as mock_get_session:
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        # Mock error response
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_response

        mock_config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Integration should still load but coordinator may have no data
        # The entry should be LOADED since we don't raise ConfigEntryNotReady
        assert mock_config_entry.state is ConfigEntryState.LOADED


async def test_async_setup_entry_old_config_format(
    hass: HomeAssistant,
    mock_api_client: MagicMock,
) -> None:
    """Test setup with old config entry format (single resource)."""
    # Create an entry with old format
    old_format_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Homevolt",
        data={
            "resource": "http://192.168.1.100/ems.json",
        },
        unique_id="old_format_entry",
        entry_id="old_format_id",
    )

    entry = await setup_integration(hass, old_format_entry)

    assert entry.state is ConfigEntryState.LOADED


async def test_service_registration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api_client: MagicMock,
) -> None:
    """Test that services are registered after setup."""
    await setup_integration(hass, mock_config_entry)

    # Check that the add_schedule service is registered
    assert hass.services.has_service(DOMAIN, "add_schedule")
