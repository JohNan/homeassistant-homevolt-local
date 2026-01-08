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
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .const import (
    CONF_ADD_ANOTHER,
    CONF_HOST,
    CONF_HOSTS,
    CONF_MAIN_HOST,
    CONF_MDNS_ID,
    CONF_RESOURCES,
    DEFAULT_READ_TIMEOUT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EMS_RESOURCE_PATH,
)
from .discovery import (
    build_base_url,
    extract_ip_or_host,
    extract_mdns_id,
    extract_port,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PASSWORD, default=""): str,
        vol.Optional(CONF_VERIFY_SSL, default=False): bool,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_READ_TIMEOUT): int,
    }
)

STEP_ADD_HOST_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_HOST, default=""): str,
        vol.Optional(CONF_ADD_ANOTHER, default=False): bool,
    }
)


# Schema for zeroconf confirmation when auth is required
STEP_ZEROCONF_CONFIRM_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_PASSWORD, default=""): str,
        vol.Optional(CONF_VERIFY_SSL, default=False): bool,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_READ_TIMEOUT): int,
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


class MissingDeviceId(Exception):
    """Error to indicate the device did not return an ecu_id."""


def is_valid_host(host: str) -> bool:
    """Check if the host is valid."""
    # Simple validation: host should not be empty and should not contain spaces
    return bool(host) and " " not in host


def normalize_host(host: str) -> str:
    """Normalize the host by removing trailing slashes."""
    return host.rstrip("/")


def construct_resource_url(host: str) -> str:
    """Construct the resource URL from the host."""
    return f"{host}{EMS_RESOURCE_PATH}"


async def try_connect(
    hass: HomeAssistant,
    url: str,
    auth: aiohttp.BasicAuth | None,
    verify_ssl: bool = True,
) -> tuple[bool, int, dict[str, Any] | None]:
    """Try to connect to a URL asynchronously.

    Returns success status, HTTP status, and data.
    """
    try:
        session = async_get_clientsession(hass, verify_ssl=verify_ssl)
        timeout = aiohttp.ClientTimeout(total=10)
        async with session.get(url, auth=auth, timeout=timeout) as response:
            status_code = response.status
            if status_code == 200:
                try:
                    data = await response.json()
                    return True, status_code, data
                except ValueError:
                    return False, status_code, None
            return False, status_code, None
    except (aiohttp.ClientError, TimeoutError):
        return False, 0, None


async def validate_host(
    hass: HomeAssistant,
    host: str,
    username: str | None = None,
    password: str | None = None,
    verify_ssl: bool = True,
    existing_hosts: list[str] | None = None,
) -> dict[str, Any]:
    """Validate a host and return its resource URL."""
    # Normalize the host
    host = normalize_host(host.strip())

    # Validate the host format
    if not is_valid_host(host):
        raise InvalidResource("Invalid IP or hostname format")

    # Determine if protocol is already specified
    has_protocol = host.startswith(("http://", "https://"))

    # Build list of URLs to try
    if has_protocol:
        # User specified protocol, use it as-is
        urls_to_try = [host]
    else:
        # No protocol specified, try http first then https
        urls_to_try = [f"http://{host}", f"https://{host}"]

    # Check if the host (without protocol) is already in the list
    host_without_protocol = host
    if has_protocol:
        host_without_protocol = host.split("://", 1)[1]

    if existing_hosts:
        for existing in existing_hosts:
            existing_without_protocol = existing
            if existing.startswith(("http://", "https://")):
                existing_without_protocol = existing.split("://", 1)[1]
            if host_without_protocol == existing_without_protocol:
                raise DuplicateHost(
                    "This IP address or hostname is already in the list"
                )

    # Try to connect
    auth = aiohttp.BasicAuth(username, password) if username and password else None

    working_host = None
    response_data = None
    last_status = 0

    for url in urls_to_try:
        resource_url = construct_resource_url(url)
        success, status, data = await try_connect(hass, resource_url, auth, verify_ssl)
        last_status = status

        if status == 401:
            # Use Home Assistant standard auth exception
            raise ConfigEntryAuthFailed()

        if success and data:
            # Check if the response has the expected structure
            if "aggregated" in data:
                working_host = url
                response_data = data
                break

    if not working_host or not response_data:
        if last_status == 401:
            raise ConfigEntryAuthFailed()
        raise ConfigEntryNotReady(
            f"Cannot connect to {host}. Tried http and https protocols."
            if not has_protocol
            else f"Cannot connect to {host}"
        )

    # Extract ecu_id from the first EMS device for stable identification
    # ecu_id is REQUIRED - without it we cannot guarantee unique identification
    ecu_id = None
    ems_list = response_data.get("ems", [])
    if ems_list and len(ems_list) > 0:
        ecu_id = ems_list[0].get("ecu_id")

    if not ecu_id:
        raise MissingDeviceId(
            f"Device at {host} did not return an ecu_id. "
            "This is required for stable device identification."
        )

    # Return the host (with working protocol), resource URL, and ecu_id
    return {
        "host": working_host,
        "resource_url": construct_resource_url(working_host),
        "ecu_id": ecu_id,
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


class HomevoltConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for Homevolt Local."""

    VERSION = 1

    _discovery_info: ZeroconfServiceInfo | dict | None = None
    _discovered_host: str | None = None
    _discovered_host_info: dict[str, Any] | None = None

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
        self.timeout: int = DEFAULT_READ_TIMEOUT

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
                # Username is always "admin" when auth is enabled
                self.password = user_input.get(CONF_PASSWORD, "").strip() or None
                self.username = "admin" if self.password else None
                self.verify_ssl = user_input.get(CONF_VERIFY_SSL, True)
                self.scan_interval = user_input.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                )
                self.timeout = user_input.get(CONF_TIMEOUT, DEFAULT_READ_TIMEOUT)

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

            except (ConfigEntryNotReady, CannotConnect) as err:
                _LOGGER.exception("Connection exception: %s", err)
                errors["base"] = "cannot_connect"
            except (ConfigEntryAuthFailed, InvalidAuth):
                errors["base"] = "invalid_auth"
            except InvalidResource:
                errors["base"] = "invalid_resource"
            except MissingDeviceId as err:
                _LOGGER.error("Device missing ecu_id: %s", err)
                errors["base"] = "missing_device_id"
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

            except (ConfigEntryNotReady, CannotConnect):
                errors["base"] = "cannot_connect"
            except (ConfigEntryAuthFailed, InvalidAuth):
                errors["base"] = "invalid_auth"
            except InvalidResource:
                errors["base"] = "invalid_resource"
            except DuplicateHost:
                errors["base"] = "duplicate_host"
            except MissingDeviceId as err:
                _LOGGER.error("Device missing ecu_id: %s", err)
                errors["base"] = "missing_device_id"
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
            # ecu_id is required - validate_host ensures it's always available
            if not self.main_ecu_id:
                # This shouldn't happen as validate_host raises MissingDeviceId
                _LOGGER.error("No ecu_id available - this should not happen")
                return self.async_abort(reason="missing_device_id")

            unique_id = str(self.main_ecu_id)

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

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle zeroconf discovery.

        Following platinum integration patterns:
        1. Extract device identifiers (MAC, serial, etc.)
        2. Set unique_id and abort if already configured (with host update)
        3. Validate device is reachable
        4. Show confirmation form
        """
        _LOGGER.debug("Zeroconf discovery: %s", discovery_info)

        # Support dict discovery_info used in tests as well as ZeroconfServiceInfo
        if isinstance(discovery_info, dict):
            name = discovery_info.get("name", "") or ""
        else:
            name = getattr(discovery_info, "name", "") or ""

        # Only handle Homevolt service name (case-insensitive)
        if "homevolt" not in name.lower():
            return self.async_abort(reason="not_homevolt")

        # Extract host information
        host = extract_ip_or_host(discovery_info)
        port = extract_port(discovery_info) or 80
        mdns_id = extract_mdns_id(discovery_info)

        if not host:
            return self.async_abort(reason="cannot_connect")

        # Use mdns_id from hostname (e.g., 68b6b34e70a0 from
        # homevolt-68b6b34e70a0.local). Fall back to host if no mdns_id found.
        unique_id = mdns_id or host
        await self.async_set_unique_id(unique_id)

        # Abort if already configured, but update host if it changed
        host_url = build_base_url(host, port)
        self._abort_if_unique_id_configured(
            updates={
                CONF_HOSTS: [host_url],
                CONF_MAIN_HOST: host_url,
            }
        )

        # Store discovery info for confirmation step
        self._discovery_info = discovery_info
        self._discovered_host = host_url
        self._discovered_host_info = None

        # Don't validate during discovery - wait for user confirmation
        # This avoids overwhelming the device with requests during mDNS discovery
        # Validation will happen in the confirm step when user clicks "Add"

        # Set title placeholder for discovery notification
        self.context["title_placeholders"] = {"name": name, "host": host}

        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm zeroconf discovery.

        If device was validated without auth, this is confirm-only.
        If device requires auth, user must enter credentials.
        """
        if not self._discovered_host:
            return self.async_abort(reason="cannot_connect")

        host_str = self._discovered_host
        errors: dict[str, str] = {}

        if user_input is not None:
            # Username is always "admin" when auth is enabled
            password = user_input.get(CONF_PASSWORD, "").strip() or None
            username = "admin" if password else None
            verify_ssl = user_input.get(CONF_VERIFY_SSL, False)

            # Reuse cached info if already validated and no new credentials
            if self._discovered_host_info and not username and not password:
                host_info = self._discovered_host_info
            else:
                # Validate with provided credentials
                try:
                    host_info = await validate_host(
                        self.hass, host_str, username, password, verify_ssl
                    )
                except (ConfigEntryAuthFailed, InvalidAuth):
                    errors["base"] = "invalid_auth"
                except (ConfigEntryNotReady, CannotConnect):
                    errors["base"] = "cannot_connect"
                except MissingDeviceId as err:
                    _LOGGER.error("Device missing ecu_id: %s", err)
                    errors["base"] = "missing_device_id"
                except Exception:
                    _LOGGER.exception("Unexpected error during validation")
                    errors["base"] = "unknown"

                if errors:
                    return self.async_show_form(
                        step_id="zeroconf_confirm",
                        data_schema=STEP_ZEROCONF_CONFIRM_SCHEMA,
                        errors=errors,
                        description_placeholders={"host": host_str},
                    )

            # Create the config entry
            return self.async_create_entry(
                title=f"Homevolt ({host_info['host']})",
                data={
                    CONF_HOSTS: [host_info["host"]],
                    CONF_MAIN_HOST: host_info["host"],
                    CONF_RESOURCES: [host_info["resource_url"]],
                    CONF_ECU_ID: host_info.get("ecu_id"),
                    CONF_MDNS_ID: self.unique_id,  # Store mdns_id for future matching
                    CONF_USERNAME: username,
                    CONF_PASSWORD: password,
                    CONF_VERIFY_SSL: verify_ssl,
                    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                    CONF_TIMEOUT: DEFAULT_READ_TIMEOUT,
                },
            )

        return self.async_show_form(
            step_id="zeroconf_confirm",
            data_schema=STEP_ZEROCONF_CONFIRM_SCHEMA,
            errors=errors,
            description_placeholders={"host": host_str},
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
                # Username is always "admin" when auth is enabled
                password = user_input.get(CONF_PASSWORD, "").strip() or None
                username = "admin" if password else None
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
                    CONF_TIMEOUT: user_input.get(CONF_TIMEOUT, DEFAULT_READ_TIMEOUT),
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

            except (ConfigEntryNotReady, CannotConnect):
                errors["base"] = "cannot_connect"
            except (ConfigEntryAuthFailed, InvalidAuth):
                errors["base"] = "invalid_auth"
            except InvalidResource:
                errors["base"] = "invalid_resource"
            except MissingDeviceId as err:
                _LOGGER.error("Device missing ecu_id: %s", err)
                errors["base"] = "missing_device_id"
            except Exception as err:
                _LOGGER.exception("Unexpected exception: %s", err)
                errors["base"] = "unknown"

        # Get current values for defaults
        current_hosts = self.config_entry.data.get(CONF_HOSTS, [])
        current_host = current_hosts[0] if current_hosts else ""
        current_password = self.config_entry.data.get(CONF_PASSWORD) or ""
        current_verify_ssl = self.config_entry.data.get(CONF_VERIFY_SSL, False)
        current_scan_interval = self.config_entry.data.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        current_timeout = self.config_entry.data.get(CONF_TIMEOUT, DEFAULT_READ_TIMEOUT)

        options_schema = vol.Schema(
            {
                vol.Optional(CONF_HOST, default=current_host): str,
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
