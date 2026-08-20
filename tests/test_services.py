"""Tests for Homevolt Local battery control service calls."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.homevolt_local.const import DOMAIN

from .conftest import setup_integration


async def test_add_schedule_service(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api_client: MagicMock,
) -> None:
    """Test add_schedule service with all parameters."""
    await setup_integration(hass, mock_config_entry)

    # Get device entry
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_device(
        identifiers={(DOMAIN, "homevolt_test_ecu_123")}
    )
    assert device is not None

    from_time = datetime(2025, 12, 15, 23, 0, 0)
    to_time = datetime(2025, 12, 16, 7, 0, 0)

    # Call add_schedule service
    await hass.services.async_call(
        DOMAIN,
        "add_schedule",
        {
            "device_id": device.id,
            "mode": "1",
            "from_time": from_time,
            "to_time": to_time,
            "max_charge": 3000,
            "max_soc": 80,
            "min_soc": 20,
            "import_limit": 5000,
            "export_limit": 4000,
        },
        blocking=True,
    )

    # Verify POST /console.json was called with correct command
    expected_cmd = (
        "sched_add 1 --from 2025-12-15T23:00:00 --to 2025-12-16T07:00:00 "
        "-c 3000 --min 20 --max 80 -l 5000 -x 4000"
    )
    post_calls = mock_api_client.post.call_args_list
    assert any(
        call.args[0].endswith("/console.json")
        and call.kwargs.get("data", {}).get("cmd") == expected_cmd
        for call in post_calls
    )


async def test_set_schedule_service_immediate_charge(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api_client: MagicMock,
) -> None:
    """Test set_schedule service for immediate battery charge."""
    await setup_integration(hass, mock_config_entry)

    device_registry = dr.async_get(hass)
    device = device_registry.async_get_device(
        identifiers={(DOMAIN, "homevolt_test_ecu_123")}
    )

    await hass.services.async_call(
        DOMAIN,
        "set_schedule",
        {
            "device_id": device.id,
            "mode": 1,
            "max_charge": 3000,
            "max_soc": 90,
        },
        blocking=True,
    )

    expected_cmd = "sched_set 1 -c 3000 --max 90"
    post_calls = mock_api_client.post.call_args_list
    assert any(
        call.args[0].endswith("/console.json")
        and call.kwargs.get("data", {}).get("cmd") == expected_cmd
        for call in post_calls
    )


async def test_set_schedule_service_immediate_discharge(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api_client: MagicMock,
) -> None:
    """Test set_schedule service for immediate battery discharge."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        DOMAIN,
        "set_schedule",
        {
            "mode": 2,
            "max_discharge": 2000,
            "min_soc": 40,
        },
        blocking=True,
    )

    expected_cmd = "sched_set 2 -d 2000 --min 40"
    post_calls = mock_api_client.post.call_args_list
    assert any(
        call.args[0].endswith("/console.json")
        and call.kwargs.get("data", {}).get("cmd") == expected_cmd
        for call in post_calls
    )


async def test_set_schedule_service_idle_offline(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api_client: MagicMock,
) -> None:
    """Test set_schedule service for idle mode with inverter offline."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        DOMAIN,
        "set_schedule",
        {
            "mode": 0,
            "offline": True,
        },
        blocking=True,
    )

    expected_cmd = "sched_set 0 -o"
    post_calls = mock_api_client.post.call_args_list
    assert any(
        call.args[0].endswith("/console.json")
        and call.kwargs.get("data", {}).get("cmd") == expected_cmd
        for call in post_calls
    )


async def test_delete_schedule_service(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api_client: MagicMock,
) -> None:
    """Test delete_schedule service."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        DOMAIN,
        "delete_schedule",
        {
            "schedule_id": 2,
        },
        blocking=True,
    )

    expected_cmd = "sched_del 2"
    post_calls = mock_api_client.post.call_args_list
    assert any(
        call.args[0].endswith("/console.json")
        and call.kwargs.get("data", {}).get("cmd") == expected_cmd
        for call in post_calls
    )


async def test_clear_schedules_service(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api_client: MagicMock,
) -> None:
    """Test clear_schedules service."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        DOMAIN,
        "clear_schedules",
        {},
        blocking=True,
    )

    expected_cmd = "sched_clear"
    post_calls = mock_api_client.post.call_args_list
    assert any(
        call.args[0].endswith("/console.json")
        and call.kwargs.get("data", {}).get("cmd") == expected_cmd
        for call in post_calls
    )


async def test_target_by_entity_id(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api_client: MagicMock,
) -> None:
    """Test service targeting by entity_id."""
    await setup_integration(hass, mock_config_entry)

    # Use switch entity as target
    await hass.services.async_call(
        DOMAIN,
        "set_schedule",
        {
            "entity_id": "switch.system_local_mode",
            "mode": 0,
        },
        blocking=True,
    )

    expected_cmd = "sched_set 0"
    post_calls = mock_api_client.post.call_args_list
    assert any(
        call.args[0].endswith("/console.json")
        and call.kwargs.get("data", {}).get("cmd") == expected_cmd
        for call in post_calls
    )
