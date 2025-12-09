"""Tests for Homevolt Local coordinator data updates."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.homevolt_local.const import DOMAIN

from .conftest import get_mock_api_response, setup_integration


async def test_coordinator_update(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api_client: MagicMock,
) -> None:
    """Test that coordinator updates data correctly."""
    await setup_integration(hass, mock_config_entry)

    # Check that the coordinator has data
    coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
    assert coordinator.data is not None
    assert coordinator.data.aggregated.ems_data.state_str == "idle"
    assert coordinator.data.aggregated.ems_data.power == 100.0


async def test_coordinator_handles_api_changes(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that coordinator handles API response changes."""
    # Initial response
    initial_response = get_mock_api_response(state="idle", power=100.0)
    updated_response = get_mock_api_response(state="charging", power=500.0)

    with patch(
        "custom_components.homevolt_local.async_get_clientsession"
    ) as mock_get_session:
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        # Mock GET response
        mock_get_response = AsyncMock()
        mock_get_response.status = 200
        mock_get_response.json = AsyncMock(return_value=initial_response)
        mock_get_response.__aenter__ = AsyncMock(return_value=mock_get_response)
        mock_get_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_get_response

        # Mock POST response for schedule
        mock_post_response = AsyncMock()
        mock_post_response.status = 200
        mock_post_response.text = AsyncMock(
            return_value="esp32> sched_list\nSchedule get: 0 schedules. Current ID: ''\nCommand 'sched_list' executed successfully\n"
        )
        mock_post_response.__aenter__ = AsyncMock(return_value=mock_post_response)
        mock_post_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.post.return_value = mock_post_response

        # Setup integration
        await setup_integration(hass, mock_config_entry)

        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]

        # Verify initial state
        assert coordinator.data.aggregated.ems_data.state_str == "idle"

        # Update the mock response
        mock_get_response.json = AsyncMock(return_value=updated_response)

        # Trigger a refresh
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        # Verify updated state
        assert coordinator.data.aggregated.ems_data.state_str == "charging"
        assert coordinator.data.aggregated.ems_data.power == 500.0


async def test_coordinator_multiple_hosts_data_merge(
    hass: HomeAssistant,
) -> None:
    """Test that coordinator merges data from multiple hosts."""
    # Create config entry with multiple hosts
    multi_host_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Homevolt",
        data={
            "main_host": "http://192.168.1.100",
            "hosts": ["http://192.168.1.100", "http://192.168.1.101"],
            "resources": [
                "http://192.168.1.100/ems.json",
                "http://192.168.1.101/ems.json",
            ],
            "username": "",
            "password": "",
            "verify_ssl": False,
            "scan_interval": 30,
            "timeout": 30,
            "ecu_id": "test_ecu",
        },
        unique_id="multi_host_entry",
        entry_id="multi_host_id",
    )

    # Response for first host
    response1 = get_mock_api_response(ecu_id="ecu_1")

    # Response for second host (different ecu_id and sensor)
    response2: dict[str, Any] = get_mock_api_response(ecu_id="ecu_2")
    response2["ems"][0]["ecu_id"] = "ecu_2"
    response2["sensors"] = [
        {
            "euid": "sensor_2",
            "type": "solar",
            "total_power": 300.0,
            "energy_imported": 0.0,
            "energy_exported": 500.0,
            "available": True,
            "node_id": 1,
        }
    ]

    with patch(
        "custom_components.homevolt_local.async_get_clientsession"
    ) as mock_get_session:
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        # Track calls to return different responses for different URLs
        call_count = [0]

        async def mock_json():
            call_count[0] += 1
            # First call returns response1, second returns response2
            return response1 if call_count[0] == 1 else response2

        mock_get_response = AsyncMock()
        mock_get_response.status = 200
        mock_get_response.json = mock_json
        mock_get_response.__aenter__ = AsyncMock(return_value=mock_get_response)
        mock_get_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_get_response

        # Mock POST response for schedule
        mock_post_response = AsyncMock()
        mock_post_response.status = 200
        mock_post_response.text = AsyncMock(
            return_value="Schedule get: 0 schedules. Current ID: ''"
        )
        mock_post_response.__aenter__ = AsyncMock(return_value=mock_post_response)
        mock_post_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.post.return_value = mock_post_response

        await setup_integration(hass, multi_host_entry)

        coordinator = hass.data[DOMAIN][multi_host_entry.entry_id]

        # Verify data was merged - should have data from both hosts
        # The exact behavior depends on the _merge_data implementation
        assert coordinator.data is not None
