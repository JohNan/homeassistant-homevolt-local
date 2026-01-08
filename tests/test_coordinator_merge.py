"""Tests for coordinator merge logic and duplicate handling."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.homevolt_local.coordinator import (
    HomevoltDataUpdateCoordinator,
)


def get_mock_response(
    ecu_id: str = "ecu_001",
    sensors: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a mock API response."""
    if sensors is None:
        sensors = [
            {
                "euid": "sensor_grid_001",
                "type": "grid",
                "total_power": 100.0,
                "available": True,
            },
            {
                "euid": "sensor_solar_001",
                "type": "solar",
                "total_power": 500.0,
                "available": True,
            },
            {
                "euid": "0000000000000000",  # Virtual load sensor
                "type": "load",
                "total_power": 200.0,
                "available": True,
            },
        ]

    return {
        "aggregated": {
            "ems_data": {"state_str": "idle", "soc_avg": 50.0, "power": 100.0},
            "error_str": "",
            "bms_data": [{"soc": 5000}],
        },
        "ems": [
            {
                "ecu_id": ecu_id,
                "ems_data": {"state_str": "idle", "soc_avg": 50.0, "power": 100.0},
                "error_str": "",
                "bms_data": [{"soc": 5000}],
            }
        ],
        "sensors": sensors,
    }


async def test_single_host_no_duplicates(
    hass: HomeAssistant,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test single host setup doesn't create duplicates."""
    caplog.set_level(logging.DEBUG)

    coordinator = HomevoltDataUpdateCoordinator(
        hass=hass,
        logger=logging.getLogger(__name__),
        entry_id="test_entry",
        resources=["http://192.168.1.100/ems.json"],
        hosts=["http://192.168.1.100"],
        main_host="http://192.168.1.100",
        ecu_id=None,
        username=None,
        password=None,
        verify_ssl=False,
        update_interval=timedelta(seconds=30),
    )

    # Mock the fetch to return data
    mock_response = get_mock_response()
    with (
        patch.object(coordinator, "_fetch_resource_data", return_value=mock_response),
        patch.object(coordinator, "_fetch_schedule_data", return_value={}),
    ):
        data = await coordinator._async_update_data()

    # Verify no duplicates
    assert len(data.sensors) == 3
    assert len(data.ems) == 1

    # Check debug logs
    assert "Valid results from 1 hosts" in caplog.text
    assert "Merge complete: final ems=1, final sensors=3" in caplog.text


async def test_multi_host_main_timeout_causes_duplicates(
    hass: HomeAssistant,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that main host timeout with fallback used to cause duplicates (now fixed)."""
    caplog.set_level(logging.DEBUG)

    # Two hosts configured, main host is first
    coordinator = HomevoltDataUpdateCoordinator(
        hass=hass,
        logger=logging.getLogger(__name__),
        entry_id="test_entry",
        resources=[
            "http://192.168.1.100/ems.json",
            "http://192.168.1.101/ems.json",
        ],
        hosts=["http://192.168.1.100", "http://192.168.1.101"],
        main_host="http://192.168.1.100",
        ecu_id=None,
        username=None,
        password=None,
        verify_ssl=False,
        update_interval=timedelta(seconds=30),
    )

    # Secondary host response (same sensors - simulating they're connected)
    secondary_response = get_mock_response(ecu_id="secondary_ecu")

    async def mock_fetch(resource: str) -> dict[str, Any]:
        if "192.168.1.100" in resource:
            # Main host times out
            raise UpdateFailed("Timeout")
        return secondary_response

    with patch.object(coordinator, "_fetch_resource_data", side_effect=mock_fetch):
        with patch.object(coordinator, "_fetch_schedule_data", return_value={}):
            data = await coordinator._async_update_data()

    # With the fix, secondary host data should be used once, not duplicated
    # Check that we have the expected counts
    assert len(data.sensors) == 3, f"Expected 3 sensors, got {len(data.sensors)}"
    assert len(data.ems) == 1, f"Expected 1 EMS, got {len(data.ems)}"

    # Verify the warning was logged
    assert "Main system data not available" in caplog.text
    assert "http://192.168.1.101" in caplog.text


async def test_multi_host_both_respond_deduplication(
    hass: HomeAssistant,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that sensors from both hosts are deduplicated correctly."""
    caplog.set_level(logging.DEBUG)

    coordinator = HomevoltDataUpdateCoordinator(
        hass=hass,
        logger=logging.getLogger(__name__),
        entry_id="test_entry",
        resources=[
            "http://192.168.1.100/ems.json",
            "http://192.168.1.101/ems.json",
        ],
        hosts=["http://192.168.1.100", "http://192.168.1.101"],
        main_host="http://192.168.1.100",
        ecu_id=None,
        username=None,
        password=None,
        verify_ssl=False,
        update_interval=timedelta(seconds=30),
    )

    # Both hosts return the SAME sensors (same euid+type)
    main_response = get_mock_response(ecu_id="main_ecu")
    secondary_response = get_mock_response(ecu_id="secondary_ecu")

    async def mock_fetch(resource: str) -> dict[str, Any]:
        if "192.168.1.100" in resource:
            return main_response
        return secondary_response

    with patch.object(coordinator, "_fetch_resource_data", side_effect=mock_fetch):
        with patch.object(coordinator, "_fetch_schedule_data", return_value={}):
            data = await coordinator._async_update_data()

    # Sensors should be deduplicated (same euid+type from both hosts)
    assert len(data.sensors) == 3, f"Expected 3 sensors, got {len(data.sensors)}"
    # EMS devices should NOT be deduplicated (different ecu_id)
    assert len(data.ems) == 2, f"Expected 2 EMS, got {len(data.ems)}"

    # Check the merge log
    assert "Skipping host http://192.168.1.100" in caplog.text


async def test_api_returns_duplicate_sensors(
    hass: HomeAssistant,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test handling when API itself returns duplicate sensors."""
    caplog.set_level(logging.DEBUG)

    coordinator = HomevoltDataUpdateCoordinator(
        hass=hass,
        logger=logging.getLogger(__name__),
        entry_id="test_entry",
        resources=["http://192.168.1.100/ems.json"],
        hosts=["http://192.168.1.100"],
        main_host="http://192.168.1.100",
        ecu_id=None,
        username=None,
        password=None,
        verify_ssl=False,
        update_interval=timedelta(seconds=30),
    )

    # API returns duplicate sensors (same euid+type twice)
    duplicate_sensors = [
        {"euid": "sensor_solar_001", "type": "solar", "total_power": 500.0},
        {
            "euid": "sensor_solar_001",
            "type": "solar",
            "total_power": 500.0,
        },  # Duplicate!
        {"euid": "sensor_grid_001", "type": "grid", "total_power": 100.0},
    ]
    mock_response = get_mock_response(sensors=duplicate_sensors)

    with (
        patch.object(coordinator, "_fetch_resource_data", return_value=mock_response),
        patch.object(coordinator, "_fetch_schedule_data", return_value={}),
    ):
        data = await coordinator._async_update_data()

    # Duplicates from the API are now deduplicated by the coordinator.
    # This was fixed because duplicate sensors could cause issues for users.
    sensor_euids = [s.euid for s in data.sensors]
    solar_count = sensor_euids.count("sensor_solar_001")

    # Log what we got for debugging
    caplog.records.clear()
    logging.getLogger(__name__).info(
        "Sensor euids: %s, solar_count: %d", sensor_euids, solar_count
    )

    # Duplicates should be filtered out
    assert solar_count == 1, (
        f"Expected 1 (duplicates filtered), got {solar_count}. "
        "Deduplication should remove duplicate sensors from the API response."
    )
