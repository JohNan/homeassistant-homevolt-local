"""Fixtures for Homevolt Local integration tests."""

from __future__ import annotations

import json
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.homevolt_local.const import (
    CONF_HOSTS,
    CONF_MAIN_HOST,
    CONF_RESOURCES,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
)

pytest_plugins = "pytest_homeassistant_custom_component"

# Path to fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(filename: str) -> str:
    """Load a fixture file."""
    return (FIXTURES_DIR / filename).read_text()


def load_json_fixture(filename: str) -> dict[str, Any]:
    """Load a JSON fixture file."""
    return json.loads(load_fixture(filename))


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Auto enable custom integrations for all tests."""
    return


def get_mock_api_response(
    state: str = "idle",
    power: float = 100.0,
    soc: int = 5000,
    ecu_id: str = "test_ecu_123",
) -> dict[str, Any]:
    """Return mock API response with configurable values."""
    return {
        "aggregated": {
            "ems_data": {
                "state_str": state,
                "soc_avg": 50.0,
                "power": power,
                "energy_produced": 1000.0,
                "energy_consumed": 500.0,
            },
            "error_str": "",
            "bms_data": [{"soc": soc}],
        },
        "ems": [
            {
                "ecu_id": ecu_id,
                "ems_data": {
                    "state_str": state,
                    "soc_avg": 50.0,
                    "power": power,
                    "energy_produced": 1000.0,
                    "energy_consumed": 500.0,
                },
                "error_str": "",
                "inv_info": {"serial_number": "inv_0"},
                "ems_info": {"fw_version": "1.0.0"},
                "bms_data": [],
            }
        ],
        "sensors": [
            {
                "euid": "sensor_0",
                "type": "grid",
                "total_power": 200.0,
                "energy_imported": 2000.0,
                "energy_exported": 1000.0,
                "available": True,
                "node_id": 0,
            }
        ],
    }


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return the default mocked config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Homevolt",
        data={
            CONF_MAIN_HOST: "http://192.168.1.100",
            CONF_HOSTS: ["http://192.168.1.100"],
            CONF_RESOURCES: ["http://192.168.1.100/ems.json"],
            CONF_USERNAME: "",
            CONF_PASSWORD: "",
            CONF_VERIFY_SSL: False,
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
            CONF_TIMEOUT: DEFAULT_TIMEOUT,
            "ecu_id": "test_ecu_123",
        },
        unique_id="test_ecu_123",
        entry_id="test_entry_id",
    )


@pytest.fixture
def mock_api_response() -> dict[str, Any]:
    """Return mock API response from fixture file."""
    return load_json_fixture("ems_response.json")


@pytest.fixture
def mock_schedule_response() -> str:
    """Return mock schedule response from fixture file."""
    return load_fixture("schedule_response.txt")


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry for config flow tests."""
    with patch(
        "custom_components.homevolt_local.async_setup_entry",
        return_value=True,
    ) as mock_setup:
        yield mock_setup


@pytest.fixture
def mock_api_client(
    mock_api_response: dict[str, Any], mock_schedule_response: str
) -> Generator[MagicMock]:
    """Mock the aiohttp client session for API calls."""
    with patch(
        "custom_components.homevolt_local.async_get_clientsession"
    ) as mock_get_session:
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        # Mock GET response for ems.json
        mock_get_response = AsyncMock()
        mock_get_response.status = 200
        mock_get_response.json = AsyncMock(return_value=mock_api_response)
        mock_get_response.__aenter__ = AsyncMock(return_value=mock_get_response)
        mock_get_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_get_response

        # Mock POST response for console commands (schedule)
        mock_post_response = AsyncMock()
        mock_post_response.status = 200
        mock_post_response.text = AsyncMock(return_value=mock_schedule_response)
        mock_post_response.__aenter__ = AsyncMock(return_value=mock_post_response)
        mock_post_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.post.return_value = mock_post_response

        yield mock_session


@pytest.fixture
def mock_config_flow_api(mock_api_response: dict[str, Any]) -> Generator[MagicMock]:
    """Mock the aiohttp client session for config flow validation."""
    with patch(
        "custom_components.homevolt_local.config_flow.async_get_clientsession"
    ) as mock_get_session:
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        # Mock successful GET response for validation
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_api_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_response

        yield mock_session


async def setup_integration(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> MockConfigEntry:
    """Set up the integration for testing."""
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    return config_entry
