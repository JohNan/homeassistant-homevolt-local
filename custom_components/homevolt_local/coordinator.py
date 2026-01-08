"""Data update coordinator for Homevolt Local integration."""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    ATTR_ECU_ID,
    ATTR_EMS,
    ATTR_EUID,
    ATTR_SENSORS,
    ATTR_TYPE,
    CONSOLE_RESOURCE_PATH,
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_READ_TIMEOUT,
    DOMAIN,
    SCHEDULE_FETCH_INTERVAL,
)
from .models import HomevoltData, ScheduleEntry

_LOGGER = logging.getLogger(__name__)

# Retry configuration with exponential backoff for poor connections
RETRY_COUNT = 3
RETRY_BACKOFF_FACTOR = 2.0  # seconds: 2, 4, 8...
RETRY_STATUS_CODES = {502, 503, 504}


class HomevoltDataUpdateCoordinator(DataUpdateCoordinator[HomevoltData]):
    """Class to manage fetching Homevolt data."""

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger,
        entry_id: str,
        resources: list[str],
        hosts: list[str],
        main_host: str,
        ecu_id: int | None,
        username: str | None,
        password: str | None,
        verify_ssl: bool,
        update_interval: timedelta,
        read_timeout: int = DEFAULT_READ_TIMEOUT,
    ) -> None:
        """Initialize."""
        self.entry_id = entry_id
        self.resources = resources
        self.hosts = hosts
        self.main_host = main_host
        self.ecu_id = ecu_id
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        # Use separate connect/read timeouts for better handling of poor connections
        # Connect timeout is fixed (fail fast if unreachable)
        # Read timeout is configurable via config flow
        self._request_timeout = (DEFAULT_CONNECT_TIMEOUT, read_timeout)

        # For backward compatibility
        self.resource = resources[0] if resources else ""

        # Track if first refresh has completed (for verbose logging on first call only)
        self._first_refresh_done = False

        # Store hass reference for session access
        self._hass = hass

        # Schedule fetch counter - only fetch every Nth EMS update to reduce load
        self._update_count = 0
        self._schedule_fetch_interval = SCHEDULE_FETCH_INTERVAL

        # Cached schedule data to use between fetches
        self._cached_schedule_data: dict[str, Any] = {
            "entries": [],
            "count": 0,
            "current_id": None,
        }

        super().__init__(hass, logger, name=DOMAIN, update_interval=update_interval)

    def _get_session(self) -> aiohttp.ClientSession:
        """Get the aiohttp session from Home Assistant."""
        return async_get_clientsession(self._hass, verify_ssl=self.verify_ssl)

    @property
    def _auth(self) -> aiohttp.BasicAuth | None:
        """Get auth object if credentials are configured."""
        if self.username and self.password:
            return aiohttp.BasicAuth(self.username, self.password)
        return None

    def _build_url(self, host: str, path: str = "") -> str:
        """Build a URL ensuring the protocol prefix is present."""
        if host.startswith(("http://", "https://")):
            base_url = host
        else:
            base_url = f"http://{host}"
        return f"{base_url}{path}"

    def _get_timeout(self) -> aiohttp.ClientTimeout:
        """Get timeout configuration for aiohttp."""
        connect_timeout, read_timeout = self._request_timeout
        return aiohttp.ClientTimeout(
            total=None,
            connect=connect_timeout,
            sock_read=read_timeout,
        )

    async def _async_get(
        self, url: str, auth: aiohttp.BasicAuth | None
    ) -> dict[str, Any]:
        """GET request with retry logic."""
        session = self._get_session()
        timeout = self._get_timeout()
        last_error: Exception | None = None

        for attempt in range(RETRY_COUNT + 1):
            try:
                async with session.get(url, auth=auth, timeout=timeout) as resp:
                    if resp.status in RETRY_STATUS_CODES and attempt < RETRY_COUNT:
                        # Retry on specific status codes
                        await asyncio.sleep(RETRY_BACKOFF_FACTOR * (2**attempt))
                        continue
                    if resp.status != 200:
                        raise UpdateFailed(
                            f"Error communicating with API: {resp.status}"
                        )
                    return await resp.json()
            except (TimeoutError, aiohttp.ClientError) as err:
                last_error = err
                if attempt < RETRY_COUNT:
                    await asyncio.sleep(RETRY_BACKOFF_FACTOR * (2**attempt))
                    continue
                raise

        # Should not reach here, but just in case
        raise UpdateFailed(f"Request failed after retries: {last_error}")

    async def _async_post(
        self, url: str, data: dict[str, str], auth: aiohttp.BasicAuth | None
    ) -> str:
        """POST request with retry logic."""
        session = self._get_session()
        timeout = self._get_timeout()
        last_error: Exception | None = None

        for attempt in range(RETRY_COUNT + 1):
            try:
                async with session.post(
                    url, data=data, auth=auth, timeout=timeout
                ) as resp:
                    if resp.status in RETRY_STATUS_CODES and attempt < RETRY_COUNT:
                        # Retry on specific status codes
                        await asyncio.sleep(RETRY_BACKOFF_FACTOR * (2**attempt))
                        continue
                    if resp.status != 200:
                        raise UpdateFailed(
                            f"Error communicating with API: {resp.status}"
                        )
                    return await resp.text()
            except (TimeoutError, aiohttp.ClientError) as err:
                last_error = err
                if attempt < RETRY_COUNT:
                    await asyncio.sleep(RETRY_BACKOFF_FACTOR * (2**attempt))
                    continue
                raise

        # Should not reach here, but just in case
        raise UpdateFailed(f"Request failed after retries: {last_error}")

    def get_main_device_id(self) -> str:
        """Get the main device identifier for unique ID generation.

        Uses ecu_id from config or data, with fallback to entry_id.
        This provides a stable identifier that doesn't change when IP changes.
        """
        # First try to use ecu_id from config (stored in config entry)
        if self.ecu_id:
            return str(self.ecu_id)
        # Then try to get it from the data
        if self.data and self.data.ems:
            try:
                first_ems = self.data.ems[0]
                if first_ems.ecu_id:
                    return str(first_ems.ecu_id)
            except (IndexError, AttributeError):
                pass
        # Fallback to entry_id which is stable across IP changes
        return self.entry_id

    async def _fetch_resource_data(self, resource: str) -> dict[str, Any]:
        """Fetch data from a single resource."""
        try:
            return await self._async_get(resource, self._auth)
        except TimeoutError as error:
            raise UpdateFailed(
                f"Timeout error fetching data from {resource}: {error}"
            ) from error
        except (aiohttp.ClientError, ValueError) as error:
            raise UpdateFailed(
                f"Error fetching data from {resource}: {error}"
            ) from error

    async def _fetch_schedule_data(self) -> dict[str, Any]:
        """Fetch schedule data from the main host."""
        url = self._build_url(self.main_host, CONSOLE_RESOURCE_PATH)
        schedule_info: dict[str, Any] = {}

        try:
            response_text = await self._async_post(
                url, {"cmd": "sched_list"}, self._auth
            )
            schedule_info = self._parse_schedule_data(response_text)

        except TimeoutError:
            self.logger.error("Timeout fetching schedule data from %s", url)
        except aiohttp.ClientError as e:
            self.logger.error("Error fetching schedule data: %s", e)
        except (ValueError, KeyError) as e:
            self.logger.error("Error parsing schedule data: %s", e)

        return schedule_info

    def _parse_schedule_data(self, response_text: str) -> dict[str, Any]:
        """Parse the schedule data from the text response."""
        schedules = []
        count = 0
        current_id = None
        lines = response_text.splitlines()

        summary_pattern = re.compile(
            r"Schedule get: (\d+) schedules. Current ID: '([^']*)'"
        )

        for line in lines:
            line = line.strip()

            summary_match = summary_pattern.match(line)
            if summary_match:
                count = int(summary_match.group(1))
                current_id = summary_match.group(2)
                continue

            if not line.startswith("id:"):
                continue

            parts = [p.strip() for p in line.split(",")]
            data = {}
            for part in parts:
                key_value = [kv.strip() for kv in part.split(":", 1)]
                if len(key_value) == 2:
                    data[key_value[0]] = key_value[1]

            if "id" not in data:
                continue

            # Parse id - skip if not a valid integer
            try:
                schedule_id = int(data["id"])
            except ValueError:
                self.logger.warning("Skipping schedule with invalid id: %s", data["id"])
                continue

            # Parse setpoint - may be a number or a string like "<max allowed>"
            setpoint: int | None = None
            if data.get("setpoint") is not None:
                try:
                    setpoint = int(data["setpoint"])
                except ValueError:
                    # setpoint might be a string like "<max allowed>"
                    pass

            schedule = ScheduleEntry(
                id=schedule_id,
                type=data.get("type"),
                from_time=data.get("from"),
                to_time=data.get("to"),
                setpoint=setpoint,
                offline=data.get("offline") == "true"
                if data.get("offline") is not None
                else None,
                max_discharge=data.get("max_discharge"),
                max_charge=data.get("max_charge"),
            )
            schedules.append(schedule)

        return {
            "entries": schedules,
            "count": count,
            "current_id": current_id,
        }

    async def _async_update_data(self) -> HomevoltData:
        """Fetch data from all Homevolt API resources."""
        if not self.resources:
            raise UpdateFailed("No resources configured")

        # Fetch EMS data from all hosts
        valid_results = await self._fetch_all_ems_data()
        if not valid_results:
            raise UpdateFailed("Failed to fetch data from any resource")

        # Get schedule data (may use cache)
        self._update_count += 1
        schedule_data = await self._get_schedule_data_with_cache()

        # Find main system data and merge
        verbose_log = self._should_log_verbose(len(valid_results))
        main_data, main_data_host = self._find_main_data(valid_results, verbose_log)

        if verbose_log:
            self._log_debug_info(
                valid_results, schedule_data, main_data, main_data_host
            )

        # Merge and build final data
        merged_dict_data = self._merge_data(
            valid_results, main_data, main_data_host, verbose_log
        )
        merged_dict_data["schedules"] = schedule_data.get("entries", [])
        merged_dict_data["schedule_count"] = schedule_data.get("count")
        merged_dict_data["schedule_current_id"] = schedule_data.get("current_id")

        self._first_refresh_done = True
        return HomevoltData.from_dict(merged_dict_data)

    async def _fetch_all_ems_data(self) -> list[tuple[str, dict[str, Any]]]:
        """Fetch EMS data from all configured hosts sequentially."""
        valid_results: list[tuple[str, dict[str, Any]]] = []
        for i, resource in enumerate(self.resources):
            try:
                result = await self._fetch_resource_data(resource)
                valid_results.append((self.hosts[i], result))
            except UpdateFailed as err:
                self.logger.error("Error fetching data from %s: %s", resource, err)
        return valid_results

    async def _get_schedule_data_with_cache(self) -> dict[str, Any]:
        """Get schedule data, fetching fresh data periodically or using cache."""
        should_fetch = (
            self._update_count == 1
            or self._update_count % self._schedule_fetch_interval == 0
        )

        if should_fetch:
            try:
                schedule_data = await self._fetch_schedule_data()
                self._cached_schedule_data = schedule_data
                return schedule_data
            except Exception as err:
                self.logger.error("Error fetching schedule data: %s", err)

        return self._cached_schedule_data

    def _should_log_verbose(self, result_count: int) -> bool:
        """Determine if verbose debug logging should be enabled."""
        return not self._first_refresh_done or result_count > 1

    def _find_main_data(
        self,
        valid_results: list[tuple[str, dict[str, Any]]],
        verbose_log: bool,
    ) -> tuple[dict[str, Any], str]:
        """Find the main system's data from results, with fallback to first result."""
        for host, data in valid_results:
            if host == self.main_host:
                return data, host

        # Fallback to first valid result
        self.logger.warning(
            "Main system data not available (main_host=%s not in %s), "
            "using first valid result from %s",
            self.main_host,
            [host for host, _ in valid_results],
            valid_results[0][0],
        )
        return valid_results[0][1], valid_results[0][0]

    def _log_debug_info(
        self,
        valid_results: list[tuple[str, dict[str, Any]]],
        schedule_data: dict[str, Any],
        main_data: dict[str, Any],
        main_data_host: str,
    ) -> None:
        """Log debug information about the update."""
        entries = schedule_data.get("entries", [])
        self.logger.debug(
            "Schedule data: count=%s, current_id=%s, entries=%d",
            schedule_data.get("count"),
            schedule_data.get("current_id"),
            len(entries),
        )
        self.logger.debug(
            "Valid results from %d hosts: %s (main_host=%s)",
            len(valid_results),
            [host for host, _ in valid_results],
            self.main_host,
        )
        self.logger.debug(
            "Using main_data from host=%s, ems_count=%d, sensor_count=%d",
            main_data_host,
            len(main_data.get(ATTR_EMS, [])),
            len(main_data.get(ATTR_SENSORS, [])),
        )

    def _merge_data(
        self,
        results: list[tuple[str, dict[str, Any]]],
        main_data: dict[str, Any],
        main_data_host: str | None = None,
        verbose_log: bool = False,
    ) -> dict[str, Any]:
        """Merge data from multiple systems."""
        # Use main_data_host if provided (handles fallback case),
        # otherwise use self.main_host
        skip_host = main_data_host if main_data_host else self.main_host

        # Start with the main system's data
        merged_data = dict(main_data)

        # Collect all EMS devices and sensors from all systems
        all_ems = merged_data.get(ATTR_EMS, [])[:]
        all_sensors = merged_data.get(ATTR_SENSORS, [])[:]

        if verbose_log:
            self.logger.debug(
                "Merge starting: skip_host=%s, initial ems=%d, initial sensors=%d",
                skip_host,
                len(all_ems),
                len(all_sensors),
            )

        for host, data in results:
            # Skip the host whose data was used to initialize merged_data
            if host == skip_host:
                if verbose_log:
                    self.logger.debug("Skipping host %s (main data source)", host)
                continue

            if verbose_log:
                self.logger.debug(
                    "Processing host %s: ems=%d, sensors=%d",
                    host,
                    len(data.get(ATTR_EMS, [])),
                    len(data.get(ATTR_SENSORS, [])),
                )

            # Add EMS devices
            if ATTR_EMS in data:
                for ems in data[ATTR_EMS]:
                    # Check if this EMS device is already in the list (based on ecu_id)
                    if ATTR_ECU_ID in ems:
                        ecu_id = ems[ATTR_ECU_ID]
                        if not any(e.get(ATTR_ECU_ID) == ecu_id for e in all_ems):
                            all_ems.append(ems)
                    else:
                        # If no ecu_id, just add it
                        all_ems.append(ems)

            # Add sensors
            if ATTR_SENSORS in data:
                for sensor in data[ATTR_SENSORS]:
                    # Check if sensor is already in list (based on euid AND type)
                    # Using both because some sensors may have default/empty
                    # euid values like "0000000000000000"
                    euid = sensor.get(ATTR_EUID)
                    sensor_type = sensor.get(ATTR_TYPE)
                    if euid and sensor_type:
                        # Check for duplicate by both euid and type
                        if not any(
                            s.get(ATTR_EUID) == euid and s.get(ATTR_TYPE) == sensor_type
                            for s in all_sensors
                        ):
                            all_sensors.append(sensor)
                    elif euid:
                        # Fallback: if no type, just check euid
                        if not any(s.get(ATTR_EUID) == euid for s in all_sensors):
                            all_sensors.append(sensor)
                    else:
                        # If no euid, just add it
                        all_sensors.append(sensor)

        # Update the merged data with all EMS devices and sensors
        merged_data[ATTR_EMS] = all_ems
        merged_data[ATTR_SENSORS] = all_sensors

        if verbose_log:
            self.logger.debug(
                "Merge complete: final ems=%d, final sensors=%d",
                len(all_ems),
                len(all_sensors),
            )

            # Debug: log sensor details for troubleshooting duplicates
            if all_sensors:
                sensor_summary = [
                    f"{s.get(ATTR_TYPE)}:{s.get(ATTR_EUID, 'no-euid')}"
                    for s in all_sensors
                ]
                self.logger.debug("Merged sensors: %s", sensor_summary)

        return merged_data
