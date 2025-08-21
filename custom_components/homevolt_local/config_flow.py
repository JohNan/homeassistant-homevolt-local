"""Config flow for Homevolt Local integration."""
from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urlparse

import aiohttp
import voluptuous as vol

class CannotConnect(Exception):
    """Error to indicate we cannot connect."""


class InvalidAuth(Exception):
    """Error to indicate there is invalid auth."""


class InvalidResource(Exception):
    """Error to indicate the resource URL is invalid."""


class DuplicateHost(Exception):
    """Error to indicate the host is already in the list."""

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
    CONF_RESOURCE,
    CONF_RESOURCES,
    DEFAULT_RESOURCE_PATH,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
)

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


async def validate_host(
    hass: HomeAssistant, 
    host: str, 
    username: str = None, 
    password: str = None, 
    verify_ssl: bool = True,
    existing_hosts: list[str] = None
) -> dict[str, Any]:
    """Validate a host and return its resource URL."""
    # Validate the host
    if not is_valid_host(host):
        raise InvalidResource("Invalid IP or hostname format")

    # Check if the host is already in the list
    if existing_hosts and host in existing_hosts:
        raise DuplicateHost("This IP address or hostname is already in the list")

    # Construct the resource URL
    resource_url = construct_resource_url(host)

    # If username and password are provided, validate the connection
    if username and password:
        session = async_get_clientsession(hass, verify_ssl=verify_ssl)
        try:
            auth = aiohttp.BasicAuth(username, password)
            async with session.get(resource_url, auth=auth) as response:
                if response.status == 401:
                    raise InvalidAuth("Invalid authentication")
                elif response.status != 200:
                    raise CannotConnect(f"Invalid response from API: {response.status}")

                try:
                    response_data = await response.json()
                except ValueError:
                    raise CannotConnect("Invalid response format (not JSON)")

                # Check if the response has the expected structure
                if "aggregated" not in response_data:
                    raise CannotConnect("Invalid API response format: 'aggregated' key missing")

        except aiohttp.ClientError as err:
            raise CannotConnect(f"Connection error: {err}")
        except (InvalidAuth, CannotConnect, InvalidResource, DuplicateHost) as err:
            raise
        except Exception as err:
            raise Exception(f"Error validating API: {err}") from err

    # Return the host and resource URL
    return {
        "host": host,
        "resource_url": resource_url
    }


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    host = data[CONF_HOST]
    username = data.get(CONF_USERNAME)
    password = data.get(CONF_PASSWORD)
    verify_ssl = data.get(CONF_VERIFY_SSL, True)
    existing_hosts = data.get(CONF_HOSTS, [])

    # Validate the host
    host_info = await validate_host(
        hass, 
        host, 
        username, 
        password, 
        verify_ssl,
        existing_hosts
    )

    # Return info that you want to store in the config entry.
    return {
        "title": "Homevolt Local", 
        "host": host_info["host"],
        "resource_url": host_info["resource_url"]
    }


class HomevoltConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Homevolt Local."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.hosts = []
        self.resources = []
        self.main_host = None
        self.username = None
        self.password = None
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
                # Store the credentials and settings
                self.username = user_input.get(CONF_USERNAME, "").strip() or None
                self.password = user_input.get(CONF_PASSWORD, "").strip() or None
                self.verify_ssl = user_input.get(CONF_VERIFY_SSL, True)
                self.scan_interval = user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                self.timeout = user_input.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)

                # Validate the first host
                host_info = await validate_host(
                    self.hass,
                    user_input[CONF_HOST],
                    self.username,
                    self.password,
                    self.verify_ssl,
                )

                # Store the host and resource URL
                self.hosts.append(host_info["host"])
                self.resources.append(host_info["resource_url"])

                # Set the main host to the first host by default
                self.main_host = host_info["host"]

                # Proceed to the add_host step
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
                    # Validate the additional host
                    host_info = await validate_host(
                        self.hass,
                        user_input[CONF_HOST],
                        self.username,
                        self.password,
                        self.verify_ssl,
                        self.hosts,
                    )

                    # Store the host and resource URL
                    self.hosts.append(host_info["host"])
                    self.resources.append(host_info["resource_url"])

                    # If the user wants to add another host, go back to the add_host step
                    if user_input.get(CONF_ADD_ANOTHER, False):
                        return await self.async_step_add_host()

                # If we have more than one host, proceed to the select_main step
                if len(self.hosts) > 1:
                    return await self.async_step_select_main()

                # Otherwise, proceed to the confirm step
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
                # Store the main host
                self.main_host = user_input[CONF_MAIN_HOST]

                # Proceed to the confirm step
                return await self.async_step_confirm()

            except Exception as err:
                _LOGGER.exception("Unexpected exception: %s", err)
                errors["base"] = "unknown"

        # Create a schema with a dropdown to select the main host
        schema = vol.Schema(
            {
                vol.Required(CONF_MAIN_HOST, default=self.hosts[0]): vol.In(self.hosts),
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
            # Check if any of the hosts are already configured
            for host in self.hosts:
                await self.async_set_unique_id(host)
                if self._async_current_entries():
                    return self.async_abort(reason="already_configured")

            # Set the unique_id to the main host
            await self.async_set_unique_id(self.main_host)

            # Create the config entry
            entry_data = {
                CONF_HOSTS: self.hosts,
                CONF_MAIN_HOST: self.main_host,
                CONF_RESOURCES: self.resources,
                CONF_USERNAME: self.username,
                CONF_PASSWORD: self.password,
                CONF_VERIFY_SSL: self.verify_ssl,
                CONF_SCAN_INTERVAL: self.scan_interval,
                CONF_TIMEOUT: self.timeout,
            }

            return self.async_create_entry(
                title=f"Homevolt Local ({len(self.hosts)} systems)",
                data=entry_data,
            )

        # Format the hosts for display
        hosts_str = ", ".join(self.hosts)

        return self.async_show_form(
            step_id="confirm",
            description_placeholders={"hosts": hosts_str},
        )
