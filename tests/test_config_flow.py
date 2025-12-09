"""Tests for Homevolt Local config flow."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.homevolt_local.const import CONF_HOST, DOMAIN


async def test_config_flow_user_step(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
    mock_config_flow_api: MagicMock,
) -> None:
    """Test the user config flow step."""
    # Start the config flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    # Submit the form with a valid host
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: "192.168.1.100",
            CONF_USERNAME: "",
            CONF_PASSWORD: "",
        },
    )
    await hass.async_block_till_done()

    # Should proceed to add_host step (to optionally add more hosts)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "add_host"


async def test_config_flow_complete_single_host(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
    mock_config_flow_api: MagicMock,
) -> None:
    """Test completing the full config flow with a single host."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Submit user step
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: "192.168.1.100",
            CONF_USERNAME: "",
            CONF_PASSWORD: "",
        },
    )
    await hass.async_block_till_done()

    # At add_host step, don't add another host (empty string means skip)
    assert result["step_id"] == "add_host"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: "",  # Empty host means done adding
        },
    )
    await hass.async_block_till_done()

    # Should now be at confirm step
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"

    # Confirm to create entry
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert "Homevolt Local" in result["title"]
    assert "http://192.168.1.100" in result["data"]["hosts"]
    assert len(mock_setup_entry.mock_calls) == 1


async def test_config_flow_cannot_connect(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test config flow when connection fails."""
    with patch(
        "custom_components.homevolt_local.config_flow.async_get_clientsession"
    ) as mock_get_session:
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        # Mock connection failure
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_response

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.100",
                CONF_USERNAME: "",
                CONF_PASSWORD: "",
            },
        )
        await hass.async_block_till_done()

        assert result["type"] is FlowResultType.FORM
        assert result["errors"]["base"] == "cannot_connect"


async def test_config_flow_invalid_auth(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test config flow when authentication fails."""
    with patch(
        "custom_components.homevolt_local.config_flow.async_get_clientsession"
    ) as mock_get_session:
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        # Mock 401 response
        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_response

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.100",
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "wrong",
            },
        )
        await hass.async_block_till_done()

        assert result["type"] is FlowResultType.FORM
        assert result["errors"]["base"] == "invalid_auth"


async def test_config_flow_invalid_host(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test config flow with invalid host format."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: "invalid host with spaces",
            CONF_USERNAME: "",
            CONF_PASSWORD: "",
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_resource"


async def test_config_flow_auto_protocol_detection(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
    mock_api_response: dict[str, Any],
) -> None:
    """Test that config flow auto-detects HTTP/HTTPS protocol."""
    with patch(
        "custom_components.homevolt_local.config_flow.async_get_clientsession"
    ) as mock_get_session:
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        # Mock successful response - validates protocol auto-detection
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_api_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_response

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        # Submit without protocol - should auto-detect
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.100",  # No protocol specified
                CONF_USERNAME: "",
                CONF_PASSWORD: "",
            },
        )
        await hass.async_block_till_done()

        # Should succeed and proceed to next step
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "add_host"

        # The session should have been called with http:// prefix first
        calls = mock_session.get.call_args_list
        assert any("http://192.168.1.100" in str(call) for call in calls)
