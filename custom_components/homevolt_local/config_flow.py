"""Config flow for Homevolt Local integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_ADD_ANOTHER,
    CONF_HOST,
    CONF_HOSTS,
    CONF_MAIN_HOST,
    CONF_RESOURCES,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
    EMS_RESOURCE_PATH,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_USERNAME, default=""): str,
        vol.Optional(CONF_PASSWORD, default=""): str,
        vol.Optional(CONF_VERIFY_SSL, default=False): bool,
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


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""


class InvalidAuth(Exception):
    """Error to indicate there is invalid auth."""


class InvalidResource(Exception):
    """Error to indicate the resource URL is invalid."""


class DuplicateHost(Exception):
    """Error to indicate the host is already in the list."""


def is_valid_host(host: str) -> bool:
    """Check if the host is valid."""
    # Simple validation: host should not be empty and should not contain spaces
    return bool(host) and " " not in host


def validate_protocol(host: str) -> bool:
    """Validate that the host string includes a protocol."""
    return host.startswith(("http://", "https://"))


def construct_resource_url(host: str) -> str:
    """Construct the resource URL from the host."""
    # If protocol is already included, just append the path
    return f"{host}{EMS_RESOURCE_PATH}"


async def validate_host(
    hass: HomeAssistant,
    host: str,
    username: str | None = None,
    password: str | None = None,
    verify_ssl: bool = True,
    existing_hosts: list[str] | None = None,
) -> dict[str, Any]:
    """Validate a host and return its resource URL."""
    # Validate the host format
    if not is_valid_host(host):
        raise InvalidResource("Invalid IP or hostname format")

    # Validate that a protocol is present
    if not validate_protocol(host):
        raise InvalidResource("Protocol (http:// or https://) is required")

    # Check if the host is already in the list
    if existing_hosts and host in existing_hosts:
        raise DuplicateHost("This IP address or hostname is already in the list")

    # Construct the resource URL
    resource_url = construct_resource_url(host)

    # Validate the connection
    session = async_get_clientsession(hass, verify_ssl=verify_ssl)
    ecu_id = None
    try:
        auth = aiohttp.BasicAuth(username, password) if username and password else None
        async with session.get(resource_url, auth=auth) as response:
            if response.status == 401:
                raise InvalidAuth("Invalid authentication")
            elif response.status != 200:
                raise CannotConnect(f"Invalid response from API: {response.status}")

            try:
                response_data = await response.json()
            except ValueError as err:
                raise CannotConnect("Invalid response format (not JSON)") from err

            # Check if the response has the expected structure
            if "aggregated" not in response_data:
                raise CannotConnect(
                    "Invalid API response format: 'aggregated' key missing"
                )

            # Extract ecu_id from the first EMS device for stable identification
            ems_list = response_data.get("ems", [])
            if ems_list and len(ems_list) > 0:
                ecu_id = ems_list[0].get("ecu_id")

    except aiohttp.ClientError as err:
        raise CannotConnect(f"Connection error: {err}") from err
    except (InvalidAuth, CannotConnect, InvalidResource, DuplicateHost):
        raise
    except Exception as err:
        raise Exception(f"Error validating API: {err}") from err

    # Return the host, resource URL, and ecu_id
    return {"host": host, "resource_url": resource_url, "ecu_id": ecu_id}


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    host = data[CONF_HOST]
    username = data.get(CONF_USERNAME)
    password = data.get(CONF_PASSWORD)
    verify_ssl = data.get(CONF_VERIFY_SSL, True)
    existing_hosts = data.get(CONF_HOSTS, [])

    # Validate the host
    host_info = await validate_host(
        hass, host, username, password, verify_ssl, existing_hosts
    )

    # Return info that you want to store in the config entry.
    return {
        "title": "Homevolt Local",
        "host": host_info["host"],
        "resource_url": host_info["resource_url"],
        "ecu_id": host_info.get("ecu_id"),
    }


# Constant for ecu_id in config entry
CONF_ECU_ID = "ecu_id"


class HomevoltConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Homevolt Local."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.hosts: list[str] = []
        self.resources: list[str] = []
        self.ecu_ids: list[int | None] = []
        self.main_host: str | None = None
        self.main_ecu_id: int | None = None
        self.username: str | None = None
        self.password: str | None = None
        self.verify_ssl: bool = True
        self.scan_interval: int = DEFAULT_SCAN_INTERVAL
        self.timeout: int = DEFAULT_TIMEOUT

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return HomevoltOptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                # Store the credentials and settings
                self.username = user_input.get(CONF_USERNAME, "").strip() or None
                self.password = user_input.get(CONF_PASSWORD, "").strip() or None
                self.verify_ssl = user_input.get(CONF_VERIFY_SSL, True)
                self.scan_interval = user_input.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                )
                self.timeout = user_input.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)

                # Validate the first host
                host_info = await validate_host(
                    self.hass,
                    user_input[CONF_HOST],
                    self.username,
                    self.password,
                    self.verify_ssl,
                )

                # Store the host, resource URL, and ecu_id
                self.hosts.append(host_info["host"])
                self.resources.append(host_info["resource_url"])
                self.ecu_ids.append(host_info.get("ecu_id"))

                # Set the main host and ecu_id to the first host by default
                self.main_host = host_info["host"]
                self.main_ecu_id = host_info.get("ecu_id")

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
    ) -> ConfigFlowResult:
        """Handle the add_host step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                if user_input.get(CONF_HOST):
                    # Validate the additional host
                    host_info = await validate_host(
                        self.hass,
                        user_input[CONF_HOST],
                        self.username,
                        self.password,
                        self.verify_ssl,
                        self.hosts,
                    )

                    # Store the host, resource URL, and ecu_id
                    self.hosts.append(host_info["host"])
                    self.resources.append(host_info["resource_url"])
                    self.ecu_ids.append(host_info.get("ecu_id"))

                    # If the user wants to add another host,
                    # go back to the add_host step
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
    ) -> ConfigFlowResult:
        """Handle the select_main step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                # Store the main host and find its corresponding ecu_id
                main_host: str = user_input[CONF_MAIN_HOST]
                self.main_host = main_host
                try:
                    main_index = self.hosts.index(main_host)
                    self.main_ecu_id = self.ecu_ids[main_index]
                except (ValueError, IndexError):
                    self.main_ecu_id = None

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
    ) -> ConfigFlowResult:
        """Handle the confirm step."""
        if user_input is not None:
            # Use ecu_id as unique identifier if available, otherwise fall back to host
            unique_id = str(self.main_ecu_id) if self.main_ecu_id else self.main_host

            # Check if already configured
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            # Create the config entry
            entry_data = {
                CONF_HOSTS: self.hosts,
                CONF_MAIN_HOST: self.main_host,
                CONF_RESOURCES: self.resources,
                CONF_ECU_ID: self.main_ecu_id,
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


class HomevoltOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Homevolt Local."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Get current values
                current_hosts = self.config_entry.data.get(CONF_HOSTS, [])
                current_main_host = self.config_entry.data.get(CONF_MAIN_HOST)
                current_ecu_id = self.config_entry.data.get(CONF_ECU_ID)
                username = user_input.get(CONF_USERNAME, "").strip() or None
                password = user_input.get(CONF_PASSWORD, "").strip() or None
                verify_ssl = user_input.get(CONF_VERIFY_SSL, False)

                # Get the new host
                new_host = user_input.get(CONF_HOST, "").strip()
                new_ecu_id = current_ecu_id

                if new_host:
                    # Validate the new host
                    host_info = await validate_host(
                        self.hass,
                        new_host,
                        username,
                        password,
                        verify_ssl,
                    )

                    # Update hosts and resources
                    new_hosts = [host_info["host"]]
                    new_resources = [host_info["resource_url"]]
                    new_main_host = host_info["host"]
                    # Keep the existing ecu_id - it should be the same device
                    # Only update if we got a new one and didn't have one before
                    if host_info.get("ecu_id") and not current_ecu_id:
                        new_ecu_id = host_info.get("ecu_id")
                else:
                    # Keep existing hosts
                    new_hosts = current_hosts
                    new_resources = self.config_entry.data.get(CONF_RESOURCES, [])
                    new_main_host = current_main_host

                # Build updated data
                new_data = {
                    CONF_HOSTS: new_hosts,
                    CONF_MAIN_HOST: new_main_host,
                    CONF_RESOURCES: new_resources,
                    CONF_ECU_ID: new_ecu_id,
                    CONF_USERNAME: username,
                    CONF_PASSWORD: password,
                    CONF_VERIFY_SSL: verify_ssl,
                    CONF_SCAN_INTERVAL: user_input.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                    CONF_TIMEOUT: user_input.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
                }

                # Update config entry data
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data=new_data,
                    title=f"Homevolt Local ({len(new_hosts)} systems)",
                )

                # Reload the integration
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)

                return self.async_create_entry(title="", data={})

            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except InvalidResource:
                errors["base"] = "invalid_resource"
            except Exception as err:
                _LOGGER.exception("Unexpected exception: %s", err)
                errors["base"] = "unknown"

        # Get current values for defaults
        current_hosts = self.config_entry.data.get(CONF_HOSTS, [])
        current_host = current_hosts[0] if current_hosts else ""
        current_username = self.config_entry.data.get(CONF_USERNAME) or ""
        current_password = self.config_entry.data.get(CONF_PASSWORD) or ""
        current_verify_ssl = self.config_entry.data.get(CONF_VERIFY_SSL, False)
        current_scan_interval = self.config_entry.data.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        current_timeout = self.config_entry.data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)

        options_schema = vol.Schema(
            {
                vol.Optional(CONF_HOST, default=current_host): str,
                vol.Optional(CONF_USERNAME, default=current_username): str,
                vol.Optional(CONF_PASSWORD, default=current_password): str,
                vol.Optional(CONF_VERIFY_SSL, default=current_verify_ssl): bool,
                vol.Optional(CONF_SCAN_INTERVAL, default=current_scan_interval): int,
                vol.Optional(CONF_TIMEOUT, default=current_timeout): int,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
            errors=errors,
        )
