"""Tests for Homevolt Local sensor platform."""

from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from syrupy.assertion import SnapshotAssertion

from .conftest import setup_integration


async def test_sensor_entities_created(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api_client: MagicMock,
) -> None:
    """Test sensor entities are created correctly."""
    await setup_integration(hass, mock_config_entry)

    # Check that sensors are created via state machine
    # The sensor entity ID format is based on the entity name
    state = hass.states.get("sensor.homevolt_status")
    assert state is not None
    # State may be "unknown" if coordinator doesn't have data
    # but entity should exist


async def test_sensor_power_entity_exists(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api_client: MagicMock,
) -> None:
    """Test power sensor entity exists."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get("sensor.homevolt_power")
    assert state is not None
    assert state.attributes.get("device_class") == "power"
    assert state.attributes.get("unit_of_measurement") == "W"


async def test_sensor_soc_entity_exists(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api_client: MagicMock,
) -> None:
    """Test state of charge sensor entity exists."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get("sensor.homevolt_total_soc")
    assert state is not None
    assert state.attributes.get("device_class") == "battery"
    assert state.attributes.get("unit_of_measurement") == "%"


async def test_sensor_energy_produced_entity_exists(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api_client: MagicMock,
) -> None:
    """Test energy produced sensor entity exists."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get("sensor.homevolt_energy_produced")
    assert state is not None
    assert state.attributes.get("device_class") == "energy"
    assert state.attributes.get("unit_of_measurement") == "kWh"


async def test_sensor_entity_registry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api_client: MagicMock,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test sensors are registered in entity registry."""
    await setup_integration(hass, mock_config_entry)

    # Check that main sensors are in the registry
    entry = entity_registry.async_get("sensor.homevolt_status")
    assert entry is not None
    assert entry.unique_id == "homevolt_local_ems_test_ecu_123"

    entry = entity_registry.async_get("sensor.homevolt_power")
    assert entry is not None
    assert entry.unique_id == "homevolt_local_power_test_ecu_123"


async def test_schedule_sensor_exists(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api_client: MagicMock,
) -> None:
    """Test schedule sensor entity exists."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get("sensor.homevolt_current_schedule")
    assert state is not None


async def test_sensor_states_snapshot(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api_client: MagicMock,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test sensor states match snapshot."""
    await setup_integration(hass, mock_config_entry)

    # Get all entity IDs for this integration
    entries = er.async_entries_for_config_entry(
        entity_registry, mock_config_entry.entry_id
    )

    # Create a dict of entity_id -> state for snapshot comparison
    states = {}
    for entry in entries:
        state = hass.states.get(entry.entity_id)
        if state:
            states[entry.entity_id] = {
                "state": state.state,
                "attributes": dict(state.attributes),
            }

    assert states == snapshot
