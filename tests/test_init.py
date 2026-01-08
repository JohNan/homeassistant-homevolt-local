"""Tests for Homevolt Local integration setup."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
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
    mock_session = MagicMock()

    # Mock error response (as async context manager)
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)
    mock_session.get = MagicMock(return_value=mock_response)

    # Mock POST response for schedule (as async context manager)
    mock_post_response = AsyncMock()
    mock_post_response.status = 500
    mock_post_response.text = AsyncMock(return_value="")
    mock_post_response.__aenter__ = AsyncMock(return_value=mock_post_response)
    mock_post_response.__aexit__ = AsyncMock(return_value=None)
    mock_session.post = MagicMock(return_value=mock_post_response)

    with patch(
        "custom_components.homevolt_local.coordinator.async_get_clientsession",
        return_value=mock_session,
    ):
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


async def test_migrate_sensor_unique_ids_grid_and_solar_types(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api_client: MagicMock,
) -> None:
    """Test that grid and solar sensors with null euid also get migrated."""
    entity_registry = er.async_get(hass)

    mock_config_entry.add_to_hass(hass)

    null_euid = "0000000000000000"

    # Create entities for grid and solar sensor types with null euid
    old_unique_ids = {
        f"{DOMAIN}_grid_power_sensor_{null_euid}": "grid",
        f"{DOMAIN}_grid_energy_imported_sensor_{null_euid}": "grid",
        f"{DOMAIN}_solar_power_sensor_{null_euid}": "solar",
        f"{DOMAIN}_solar_energy_exported_sensor_{null_euid}": "solar",
    }

    for old_uid in old_unique_ids:
        entity_registry.async_get_or_create(
            Platform.SENSOR,
            DOMAIN,
            old_uid,
            config_entry=mock_config_entry,
        )

    # Set up integration (triggers migration)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    main_device_id = mock_config_entry.data.get("ecu_id", mock_config_entry.entry_id)

    # Verify all sensors were migrated with correct sensor type suffix
    for old_uid, sensor_type in old_unique_ids.items():
        # Extract key from old unique ID
        key = old_uid.replace(f"{DOMAIN}_", "").replace(f"_sensor_{null_euid}", "")
        new_uid = f"{DOMAIN}_{key}_{main_device_id}_{sensor_type}"

        # Old should not exist
        entity_id = entity_registry.async_get_entity_id(
            Platform.SENSOR, DOMAIN, old_uid
        )
        assert entity_id is None, f"Old unique_id {old_uid} should not exist"

        # New should exist
        entity_id = entity_registry.async_get_entity_id(
            Platform.SENSOR, DOMAIN, new_uid
        )
        assert entity_id is not None, f"New unique_id {new_uid} should exist"


async def test_migrate_sensor_unique_ids_skipped_when_already_migrated(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api_client: MagicMock,
) -> None:
    """Test that migration is skipped when new unique ID already exists."""
    entity_registry = er.async_get(hass)

    mock_config_entry.add_to_hass(hass)

    null_euid = "0000000000000000"
    main_device_id = mock_config_entry.data.get("ecu_id", mock_config_entry.entry_id)

    # Old format unique ID
    old_unique_id = f"{DOMAIN}_load_power_sensor_{null_euid}"
    # New format unique ID (already migrated)
    new_unique_id = f"{DOMAIN}_load_power_{main_device_id}_load"

    # Create BOTH old and new entities (simulates partial migration or collision)
    entity_registry.async_get_or_create(
        Platform.SENSOR,
        DOMAIN,
        old_unique_id,
        config_entry=mock_config_entry,
    )
    entity_registry.async_get_or_create(
        Platform.SENSOR,
        DOMAIN,
        new_unique_id,
        config_entry=mock_config_entry,
    )

    # Both should exist before setup
    assert (
        entity_registry.async_get_entity_id(Platform.SENSOR, DOMAIN, old_unique_id)
        is not None
    )
    assert (
        entity_registry.async_get_entity_id(Platform.SENSOR, DOMAIN, new_unique_id)
        is not None
    )

    # Set up integration
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Both should STILL exist - old one was not migrated because new already exists
    assert (
        entity_registry.async_get_entity_id(Platform.SENSOR, DOMAIN, old_unique_id)
        is not None
    ), "Old entity should remain when migration is skipped"
    assert (
        entity_registry.async_get_entity_id(Platform.SENSOR, DOMAIN, new_unique_id)
        is not None
    ), "New entity should still exist"


async def test_migrate_sensor_unique_ids_logs_migration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api_client: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that migration logs info messages."""
    import logging

    entity_registry = er.async_get(hass)

    mock_config_entry.add_to_hass(hass)

    null_euid = "0000000000000000"
    old_unique_id = f"{DOMAIN}_load_power_sensor_{null_euid}"

    entity_registry.async_get_or_create(
        Platform.SENSOR,
        DOMAIN,
        old_unique_id,
        config_entry=mock_config_entry,
    )

    # Set up integration with logging captured
    with caplog.at_level(logging.INFO):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    # Check that migration was logged
    assert any(
        "Migrating entity" in record.message and "load_power" in record.message
        for record in caplog.records
    ), "Migration should be logged"


async def test_migrate_sensor_unique_ids_logs_skip_when_exists(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api_client: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that skipped migration logs debug message when new ID exists."""
    import logging

    entity_registry = er.async_get(hass)

    mock_config_entry.add_to_hass(hass)

    null_euid = "0000000000000000"
    main_device_id = mock_config_entry.data.get("ecu_id", mock_config_entry.entry_id)

    old_unique_id = f"{DOMAIN}_load_power_sensor_{null_euid}"
    new_unique_id = f"{DOMAIN}_load_power_{main_device_id}_load"

    # Create both old and new
    entity_registry.async_get_or_create(
        Platform.SENSOR,
        DOMAIN,
        old_unique_id,
        config_entry=mock_config_entry,
    )
    entity_registry.async_get_or_create(
        Platform.SENSOR,
        DOMAIN,
        new_unique_id,
        config_entry=mock_config_entry,
    )

    # Set up integration with debug logging captured
    with caplog.at_level(logging.DEBUG):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    # Check that skip was logged at debug level
    assert any(
        "Cannot migrate" in record.message and "already exists" in record.message
        for record in caplog.records
    ), "Skipped migration should be logged at debug level"
