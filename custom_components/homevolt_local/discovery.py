"""Helper utilities for mDNS / Zeroconf discovery for Homevolt Local.

This module centralizes parsing of ZeroconfServiceInfo objects and
extracting host, port, mdns id and mac address. This mirrors patterns
used by platinum integrations to keep config flows concise and testable.
"""

from __future__ import annotations

import re

from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo


def extract_hostname(discovery_info: ZeroconfServiceInfo | dict) -> str | None:
    """Return a sensible hostname string for the discovery info.

    Supports both ZeroconfServiceInfo objects and the dict used in tests.
    """
    if isinstance(discovery_info, dict):
        return discovery_info.get("hostname") or discovery_info.get("name")

    # Prefer the hostname, fall back to name for readability
    name = getattr(discovery_info, "hostname", None) or getattr(
        discovery_info, "name", None
    )
    return name


def extract_ip_or_host(discovery_info: ZeroconfServiceInfo | dict) -> str | None:
    """Return the best host/ip for contacting the discovered device.

    Supports ZeroconfServiceInfo objects and dicts used in tests.
    """
    if isinstance(discovery_info, dict):
        host = (
            discovery_info.get("host")
            or discovery_info.get("hostname")
            or discovery_info.get("ip_address")
        )
        return str(host) if host is not None else None

    host = getattr(discovery_info, "host", None) or getattr(
        discovery_info, "hostname", None
    )
    if not host and getattr(discovery_info, "ip_address", None):
        host = str(discovery_info.ip_address)
    return host


def extract_port(discovery_info: ZeroconfServiceInfo | dict) -> int | None:
    """Return the port advertised by zeroconf, or None.

    Supports both ZeroconfServiceInfo objects and dicts used in tests.
    """
    if isinstance(discovery_info, dict):
        port = discovery_info.get("port")
        return int(port) if port else None

    port = getattr(discovery_info, "port", None)
    return int(port) if port else None


def build_base_url(host: str, port: int | None) -> str:
    """Construct a base http:// URL including port when non-standard."""
    if port and port != 80:
        return f"http://{host}:{port}"
    return f"http://{host}"


# Match exactly 12 hex characters (MAC address without separators)
MDNS_ID_RE = re.compile(r"([0-9a-f]{12})", re.IGNORECASE)


def extract_mdns_id(discovery_info: ZeroconfServiceInfo | dict) -> str | None:
    """Try to extract an mdns id or device id from the hostname/instance name."""
    hostname = extract_hostname(discovery_info) or ""
    m = MDNS_ID_RE.search(hostname)
    if m:
        return m.group(1).lower()
    return None


def extract_mac(discovery_info: ZeroconfServiceInfo | dict) -> str | None:
    """Try to extract a MAC/deviceid from the discovered service properties.

    Returns a normalized MAC string (AA:BB:CC:...) or None.
    """
    if isinstance(discovery_info, dict):
        props = discovery_info.get("properties", {}) or {}
    else:
        props = getattr(discovery_info, "properties", {}) or {}

    device_raw = props.get("deviceid") or props.get(b"deviceid")
    if not device_raw:
        return None

    device_id = (
        device_raw.decode()
        if isinstance(device_raw, (bytes, bytearray))
        else str(device_raw)
    )
    try:
        return format_mac(device_id)
    except (ValueError, TypeError):
        return None
