"""Data update coordinator for Homevolt Local integration."""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import timedelta
from typing import Any

import aiohttp
import async_timeout
from homeassistant.core import HomeAssistant
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
    DOMAIN,
)
from .models import HomevoltData, ScheduleEntry


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
        session: aiohttp.ClientSession,
        update_interval: timedelta,
        timeout: int,
    ) -> None:
        """Initialize."""
        self.entry_id = entry_id
        self.resources = resources
        self.hosts = hosts
        self.main_host = main_host
        self.ecu_id = ecu_id
        self.username = username
        self.password = password
        self.session = session
        self.timeout = timeout

        # For backward compatibility
        self.resource = resources[0] if resources else ""

        super().__init__(hass, logger, name=DOMAIN, update_interval=update_interval)

    async def _fetch_resource_data(self, resource: str) -> dict[str, Any]:
        """Fetch data from a single resource."""
        try:
            async with async_timeout.timeout(self.timeout):
                # Only use authentication if both username and password are provided
                auth = None
                if self.username and self.password:
                    auth = aiohttp.BasicAuth(self.username, self.password)

                async with self.session.get(resource, auth=auth) as resp:
                    if resp.status != 200:
                        raise UpdateFailed(
                            f"Error communicating with API: {resp.status}"
                        )
                    return await resp.json()
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
        # Ensure URL has protocol
        if self.main_host.startswith(("http://", "https://")):
            base_url = self.main_host
        else:
            base_url = f"http://{self.main_host}"
        url = f"{base_url}{CONSOLE_RESOURCE_PATH}"
        command = "sched_list"
        schedule_info: dict[str, Any] = {}

        try:
            async with async_timeout.timeout(self.timeout):
                form_data = aiohttp.FormData()
                form_data.add_field("cmd", command)
                auth = (
                    aiohttp.BasicAuth(self.username, self.password)
                    if self.username and self.password
                    else None
                )

                async with self.session.post(
                    url, data=form_data, auth=auth
                ) as response:
                    if response.status != 200:
                        self.logger.error(
                            "Failed to fetch schedule data. Status: %s",
                            response.status,
                        )
                        return {}

                    response_text = await response.text()
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

        # Fetch sensor and schedule data in parallel
        tasks = [self._fetch_resource_data(resource) for resource in self.resources]
        tasks.append(self._fetch_schedule_data())
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Separate schedule data from sensor data results
        schedule_result = results.pop()
        schedule_data: dict[str, Any]
        if isinstance(schedule_result, Exception):
            self.logger.error("Error fetching schedule data: %s", schedule_result)
            schedule_data = {
                "entries": [],
                "count": 0,
                "current_id": None,
            }
        elif isinstance(schedule_result, dict):
            schedule_data = schedule_result
        else:
            schedule_data = {"entries": [], "count": 0, "current_id": None}

        # Process the sensor data results
        valid_results: list[tuple[str, dict[str, Any]]] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(
                    "Error fetching data from %s: %s", self.resources[i], result
                )
            elif isinstance(result, dict):
                valid_results.append((self.hosts[i], result))

        if not valid_results:
            raise UpdateFailed("Failed to fetch data from any resource")

        # Find the main system's data
        main_data = None
        for host, data in valid_results:
            if host == self.main_host:
                main_data = data
                break

        # If main system's data is not available, use the first valid result
        if main_data is None:
            self.logger.warning(
                "Main system data not available, using first valid result"
            )
            main_data = valid_results[0][1]

        # Merge data from all systems
        merged_dict_data = self._merge_data(valid_results, main_data)

        # Add schedule data to the merged data
        merged_dict_data["schedules"] = schedule_data.get("entries", [])
        merged_dict_data["schedule_count"] = schedule_data.get("count")
        merged_dict_data["schedule_current_id"] = schedule_data.get("current_id")

        # Convert the merged dictionary data to a HomevoltData object
        return HomevoltData.from_dict(merged_dict_data)

    def _merge_data(
        self, results: list[tuple[str, dict[str, Any]]], main_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Merge data from multiple systems."""
        # Start with the main system's data
        merged_data = dict(main_data)

        # Collect all EMS devices and sensors from all systems
        all_ems = merged_data.get(ATTR_EMS, [])[:]
        all_sensors = merged_data.get(ATTR_SENSORS, [])[:]

        for _, data in results:
            # Skip if this is the main_data (already used to initialize merged_data)
            if data is main_data:
                continue
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

        return merged_data
