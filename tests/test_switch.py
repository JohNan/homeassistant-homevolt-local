"""Tests for Homevolt Local switch platform."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.homevolt_local.const import DOMAIN

from .conftest import setup_integration


async def test_switch_setup(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api_client: MagicMock,
) -> None:
    """Test that switch entities are set up correctly."""
    await setup_integration(hass, mock_config_entry)

    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id(
        SWITCH_DOMAIN,
        DOMAIN,
        f"{DOMAIN}_local_mode_test_ecu_123",
    )
    assert entity_id is not None

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == STATE_OFF


async def test_switch_turn_on_off(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api_client: MagicMock,
) -> None:
    """Test turning the local mode switch on and off."""
    await setup_integration(hass, mock_config_entry)

    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id(
        SWITCH_DOMAIN,
        DOMAIN,
        f"{DOMAIN}_local_mode_test_ecu_123",
    )
    assert entity_id is not None

    # Turn on
    await hass.services.async_call(
        SWITCH_DOMAIN,
        "turn_on",
        {"entity_id": entity_id},
        blocking=True,
    )

    # Verify POST /params.json was called with k=settings_local, v=1, store=1
    post_calls = mock_api_client.post.call_args_list
    assert any(
        call.args[0].endswith("/params.json")
        and call.kwargs.get("data", {}).get("k") == "settings_local"
        and call.kwargs.get("data", {}).get("v") == "1"
        for call in post_calls
    )

    state = hass.states.get(entity_id)
    assert state.state == STATE_ON

    # Turn off
    await hass.services.async_call(
        SWITCH_DOMAIN,
        "turn_off",
        {"entity_id": entity_id},
        blocking=True,
    )

    # Verify POST /params.json was called with k=settings_local, v=0, store=1
    post_calls = mock_api_client.post.call_args_list
    assert any(
        call.args[0].endswith("/params.json")
        and call.kwargs.get("data", {}).get("k") == "settings_local"
        and call.kwargs.get("data", {}).get("v") == "0"
        for call in post_calls
    )

    state = hass.states.get(entity_id)
    assert state.state == STATE_OFF


async def test_switch_state_from_schedule_json(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api_response: dict,
    mock_schedule_response: str,
) -> None:
    """Test switch initializes state from /schedule.json when available."""
    mock_session = MagicMock()

    def mock_get_side_effect(url, **kwargs):
        resp = AsyncMock()
        resp.status = 200
        if "/schedule.json" in url:
            resp.json = AsyncMock(return_value={"local_mode": True, "schedule": []})
        else:
            resp.json = AsyncMock(return_value=mock_api_response)
        resp.__aenter__ = AsyncMock(return_value=resp)
        resp.__aexit__ = AsyncMock(return_value=None)
        return resp

    mock_session.get = MagicMock(side_effect=mock_get_side_effect)

    mock_post_resp = AsyncMock()
    mock_post_resp.status = 200
    mock_post_resp.text = AsyncMock(return_value=mock_schedule_response)
    mock_post_resp.__aenter__ = AsyncMock(return_value=mock_post_resp)
    mock_post_resp.__aexit__ = AsyncMock(return_value=None)
    mock_session.post = MagicMock(return_value=mock_post_resp)

    with patch(
        "custom_components.homevolt_local.coordinator.async_get_clientsession",
        return_value=mock_session,
    ):
        await setup_integration(hass, mock_config_entry)

        entity_registry = er.async_get(hass)
        entity_id = entity_registry.async_get_entity_id(
            SWITCH_DOMAIN,
            DOMAIN,
            f"{DOMAIN}_local_mode_test_ecu_123",
        )
        assert entity_id is not None
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == STATE_ON
