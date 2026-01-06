"""Tests for Homevolt Local integration setup."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
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

        # When API fails on initial fetch, integration should retry setup
        assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


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


async def test_migrate_sensor_unique_ids_null_euid(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api_client: MagicMock,
) -> None:
    """Test that sensors with null euid get their unique IDs migrated."""
    # Get entity registry
    entity_registry = er.async_get(hass)

    # Add the config entry first (but don't set it up yet)
    mock_config_entry.add_to_hass(hass)

    # Create entities with old unique ID format (null euid)
    null_euid = "0000000000000000"
    old_unique_ids = [
        f"{DOMAIN}_load_power_sensor_{null_euid}",
        f"{DOMAIN}_load_energy_imported_sensor_{null_euid}",
        f"{DOMAIN}_load_energy_exported_sensor_{null_euid}",
    ]

    # Register entities with old unique IDs before setup
    for old_uid in old_unique_ids:
        entity_registry.async_get_or_create(
            Platform.SENSOR,
            DOMAIN,
            old_uid,
            config_entry=mock_config_entry,
        )

    # Verify entities exist with old unique IDs
    for old_uid in old_unique_ids:
        entity_id = entity_registry.async_get_entity_id(
            Platform.SENSOR, DOMAIN, old_uid
        )
        assert entity_id is not None, f"Entity with unique_id {old_uid} should exist"

    # Now set up the integration (this triggers migration)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Expected new unique IDs use main_device_id (ecu_id from config) + sensor_type
    main_device_id = mock_config_entry.data.get("ecu_id", mock_config_entry.entry_id)
    expected_new_unique_ids = [
        f"{DOMAIN}_load_power_{main_device_id}_load",
        f"{DOMAIN}_load_energy_imported_{main_device_id}_load",
        f"{DOMAIN}_load_energy_exported_{main_device_id}_load",
    ]

    # Verify entities have been migrated to new unique IDs
    for new_uid in expected_new_unique_ids:
        entity_id = entity_registry.async_get_entity_id(
            Platform.SENSOR, DOMAIN, new_uid
        )
        assert (
            entity_id is not None
        ), f"Entity with new unique_id {new_uid} should exist"

    # Verify old unique IDs no longer exist
    for old_uid in old_unique_ids:
        entity_id = entity_registry.async_get_entity_id(
            Platform.SENSOR, DOMAIN, old_uid
        )
        assert (
            entity_id is None
        ), f"Entity with old unique_id {old_uid} should not exist"


async def test_migrate_sensor_unique_ids_real_euid_unchanged(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api_client: MagicMock,
) -> None:
    """Test that sensors with real euid are NOT migrated."""
    entity_registry = er.async_get(hass)

    mock_config_entry.add_to_hass(hass)

    # Create entity with real euid (should NOT be migrated)
    real_euid = "a46dd4fffea29595"
    old_unique_id = f"{DOMAIN}_solar_power_sensor_{real_euid}"

    entity_registry.async_get_or_create(
        Platform.SENSOR,
        DOMAIN,
        old_unique_id,
        config_entry=mock_config_entry,
    )

    # Verify entity exists
    entity_id = entity_registry.async_get_entity_id(
        Platform.SENSOR, DOMAIN, old_unique_id
    )
    assert entity_id is not None

    # Set up integration
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Entity should still have the same unique ID (not migrated)
    entity_id = entity_registry.async_get_entity_id(
        Platform.SENSOR, DOMAIN, old_unique_id
    )
    assert entity_id is not None, "Entity with real euid should NOT be migrated"
