"""Config flow for Homevolt Local integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_ADD_ANOTHER,
    CONF_HOST,
    CONF_HOSTS,
    CONF_MAIN_HOST,
    CONF_RESOURCES,
    DEFAULT_RESOURCE_PATH,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
)


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""


class InvalidAuth(Exception):
    """Error to indicate there is invalid auth."""


class InvalidResource(Exception):
    """Error to indicate the resource URL is invalid."""


class DuplicateHost(Exception):
    """Error to indicate the host is already in the list."""


_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_USERNAME, default=""): str,
        vol.Optional(CONF_PASSWORD, default=""): str,
        vol.Optional(CONF_VERIFY_SSL, default=True): bool,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): int,
    }
)

STEP_ADD_HOST_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_HOST, default=""): str,
        vol.Optional(CONF_ADD_ANOTHER, default=False): bool,
    }
)


def is_valid_host(host: str) -> bool:
    """Check if the host is valid."""
    # Simple validation: host should not be empty and should not contain spaces
    return bool(host) and " " not in host


def construct_resource_url(host: str) -> str:
    """Construct the resource URL from the host."""
    # Check if the host already includes a protocol (http:// or https://)
    if not host.startswith(("http://", "https://")):
        # Default to https if no protocol is specified
        resource_url = f"https://{host}{DEFAULT_RESOURCE_PATH}"
    else:
        # If protocol is already included, just append the path
        resource_url = f"{host}{DEFAULT_RESOURCE_PATH}"
    return resource_url


async def _validate_connection(
    session: aiohttp.ClientSession, resource_url: str, auth: aiohttp.BasicAuth | None
):
    """Validate the connection to the host."""
    async with session.get(resource_url, auth=auth) as response:
        if response.status == 401:
            raise InvalidAuth("Invalid authentication")
        if response.status != 200:
            raise CannotConnect(f"Invalid response from API: {response.status}")

        try:
            response_data = await response.json()
        except ValueError as err:
            raise CannotConnect("Invalid response format (not JSON)") from err

        if "aggregated" not in response_data:
            raise CannotConnect("Invalid API response format: 'aggregated' key missing")


async def validate_host(
    hass: HomeAssistant,
    host: str,
    username: str | None = None,
    password: str | None = None,
    verify_ssl: bool = True,
    existing_hosts: list[str] | None = None,
) -> dict[str, Any]:
    """Validate a host and return its resource URL."""
    if not is_valid_host(host):
        raise InvalidResource("Invalid IP or hostname format")

    if existing_hosts and host in existing_hosts:
        raise DuplicateHost("This IP address or hostname is already in the list")

    resource_url = construct_resource_url(host)

    if username and password:
        session = async_get_clientsession(hass, verify_ssl=verify_ssl)
        try:
            auth = aiohttp.BasicAuth(username, password)
            await _validate_connection(session, resource_url, auth)
        except aiohttp.ClientError as err:
            raise CannotConnect(f"Connection error: {err}") from err
        except (InvalidAuth, CannotConnect, InvalidResource, DuplicateHost):
            raise
        except Exception as err:
            raise Exception(f"Error validating API: {err}") from err

    return {"host": host, "resource_url": resource_url}


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    host = data[CONF_HOST]
    username = data.get(CONF_USERNAME)
    password = data.get(CONF_PASSWORD)
    verify_ssl = data.get(CONF_VERIFY_SSL, True)
    existing_hosts = data.get(CONF_HOSTS, [])

    host_info = await validate_host(
        hass, host, username, password, verify_ssl, existing_hosts
    )

    return {
        "title": "Homevolt Local",
        "host": host_info["host"],
        "resource_url": host_info["resource_url"],
    }


class HomevoltConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Homevolt Local."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.hosts: list[str] = []
        self.resources: list[str] = []
        self.main_host: str | None = None
        self.username: str | None = None
        self.password: str | None = None
        self.verify_ssl = True
        self.scan_interval = DEFAULT_SCAN_INTERVAL
        self.timeout = DEFAULT_TIMEOUT

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                self.username = user_input.get(CONF_USERNAME, "").strip() or None
                self.password = user_input.get(CONF_PASSWORD, "").strip() or None
                self.verify_ssl = user_input.get(CONF_VERIFY_SSL, True)
                self.scan_interval = user_input.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                )
                self.timeout = user_input.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)

                host_info = await validate_host(
                    self.hass,
                    user_input[CONF_HOST],
                    self.username,
                    self.password,
                    self.verify_ssl,
                )

                self.hosts.append(host_info["host"])
                self.resources.append(host_info["resource_url"])
                self.main_host = host_info["host"]

                return await self.async_step_add_host()

            except CannotConnect as err:
                _LOGGER.exception("Connection exception: %s", err)
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except InvalidResource:
                errors["base"] = "invalid_resource"
            except Exception as err:
                _LOGGER.exception("Unexpected exception: %s", err)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_add_host(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the add_host step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                if CONF_HOST in user_input and user_input[CONF_HOST]:
                    host_info = await validate_host(
                        self.hass,
                        user_input[CONF_HOST],
                        self.username,
                        self.password,
                        self.verify_ssl,
                        self.hosts,
                    )
                    self.hosts.append(host_info["host"])
                    self.resources.append(host_info["resource_url"])

                    if user_input.get(CONF_ADD_ANOTHER, False):
                        return await self.async_step_add_host()

                if len(self.hosts) > 1:
                    return await self.async_step_select_main()

                return await self.async_step_confirm()

            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except InvalidResource:
                errors["base"] = "invalid_resource"
            except DuplicateHost:
                errors["base"] = "duplicate_host"
            except Exception as err:
                _LOGGER.exception("Unexpected exception: %s", err)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="add_host", data_schema=STEP_ADD_HOST_DATA_SCHEMA, errors=errors
        )

    async def async_step_select_main(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the select_main step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                self.main_host = user_input[CONF_MAIN_HOST]
                return await self.async_step_confirm()
            except Exception as err:
                _LOGGER.exception("Unexpected exception: %s", err)
                errors["base"] = "unknown"

        schema = vol.Schema(
            {
                vol.Required(CONF_MAIN_HOST, default=self.hosts[0]): vol.In(
                    self.hosts
                ),
            }
        )
        return self.async_show_form(
            step_id="select_main", data_schema=schema, errors=errors
        )

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the confirm step."""
        if user_input is not None:
            for host in self.hosts:
                await self.async_set_unique_id(host)
                if self._async_current_entries():
                    return self.async_abort(reason="already_configured")

            if self.main_host:
                await self.async_set_unique_id(self.main_host)

            return self.async_create_entry(
                title=f"Homevolt Local ({len(self.hosts)} systems)",
                data={
                    CONF_HOSTS: self.hosts,
                    CONF_MAIN_HOST: self.main_host,
                    CONF_RESOURCES: self.resources,
                    CONF_USERNAME: self.username,
                    CONF_PASSWORD: self.password,
                    CONF_VERIFY_SSL: self.verify_ssl,
                    CONF_SCAN_INTERVAL: self.scan_interval,
                    CONF_TIMEOUT: self.timeout,
                },
            )

        return self.async_show_form(
            step_id="confirm",
            description_placeholders={"hosts": ", ".join(self.hosts)},
        )
