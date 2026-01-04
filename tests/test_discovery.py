"""Tests for Homevolt Local discovery helpers."""

from __future__ import annotations

from custom_components.homevolt_local.discovery import (
    build_base_url,
    extract_hostname,
    extract_ip_or_host,
    extract_mac,
    extract_mdns_id,
    extract_port,
)


class TestExtractHostname:
    """Tests for extract_hostname function."""

    def test_dict_with_hostname(self) -> None:
        """Test extracting hostname from dict with hostname key."""
        info = {"hostname": "homevolt-abc123.local", "name": "Homevolt"}
        assert extract_hostname(info) == "homevolt-abc123.local"

    def test_dict_with_name_only(self) -> None:
        """Test extracting hostname from dict with only name key."""
        info = {"name": "Homevolt Device"}
        assert extract_hostname(info) == "Homevolt Device"

    def test_dict_empty(self) -> None:
        """Test extracting hostname from empty dict."""
        assert extract_hostname({}) is None


class TestExtractIpOrHost:
    """Tests for extract_ip_or_host function."""

    def test_dict_with_host(self) -> None:
        """Test extracting host from dict."""
        info = {"host": "192.168.1.100", "hostname": "homevolt.local"}
        assert extract_ip_or_host(info) == "192.168.1.100"

    def test_dict_with_hostname_fallback(self) -> None:
        """Test extracting hostname when host not present."""
        info = {"hostname": "homevolt.local"}
        assert extract_ip_or_host(info) == "homevolt.local"

    def test_dict_with_ip_address_fallback(self) -> None:
        """Test extracting ip_address as fallback."""
        info = {"ip_address": "10.0.0.50"}
        assert extract_ip_or_host(info) == "10.0.0.50"

    def test_dict_empty(self) -> None:
        """Test extracting from empty dict."""
        assert extract_ip_or_host({}) is None


class TestExtractPort:
    """Tests for extract_port function."""

    def test_dict_with_port(self) -> None:
        """Test extracting port from dict."""
        info = {"port": 8080}
        assert extract_port(info) == 8080

    def test_dict_with_string_port(self) -> None:
        """Test extracting string port from dict."""
        info = {"port": "443"}
        assert extract_port(info) == 443

    def test_dict_without_port(self) -> None:
        """Test extracting port when not present."""
        info = {"host": "192.168.1.100"}
        assert extract_port(info) is None

    def test_dict_with_zero_port(self) -> None:
        """Test extracting zero port returns None."""
        info = {"port": 0}
        assert extract_port(info) is None


class TestBuildBaseUrl:
    """Tests for build_base_url function."""

    def test_standard_port_80(self) -> None:
        """Test URL with standard port 80 omits port."""
        assert build_base_url("192.168.1.100", 80) == "http://192.168.1.100"

    def test_none_port(self) -> None:
        """Test URL with None port omits port."""
        assert build_base_url("192.168.1.100", None) == "http://192.168.1.100"

    def test_custom_port(self) -> None:
        """Test URL with custom port includes port."""
        assert build_base_url("192.168.1.100", 8080) == "http://192.168.1.100:8080"

    def test_hostname(self) -> None:
        """Test URL with hostname."""
        assert build_base_url("homevolt.local", 80) == "http://homevolt.local"


class TestExtractMdnsId:
    """Tests for extract_mdns_id function."""

    def test_hostname_with_hex_id(self) -> None:
        """Test extracting hex ID from hostname like homevolt-68b6b34e70a0.local."""
        info = {"hostname": "homevolt-68b6b34e70a0.local"}
        assert extract_mdns_id(info) == "68b6b34e70a0"

    def test_hostname_uppercase_normalized(self) -> None:
        """Test that uppercase hex IDs are normalized to lowercase."""
        info = {"hostname": "Homevolt-68B6B34E70A0.local"}
        assert extract_mdns_id(info) == "68b6b34e70a0"

    def test_name_with_hex_id(self) -> None:
        """Test extracting hex ID from name field."""
        info = {"name": "homevolt-abc123def456"}
        assert extract_mdns_id(info) == "abc123def456"

    def test_no_hex_id(self) -> None:
        """Test returns None when no hex ID found."""
        info = {"hostname": "homevolt.local"}
        assert extract_mdns_id(info) is None

    def test_short_hex_rejected(self) -> None:
        """Test that short hex strings (< 12 chars) are rejected."""
        info = {"hostname": "homevolt-abc123.local"}  # Only 6 chars
        assert extract_mdns_id(info) is None

    def test_11_char_hex_rejected(self) -> None:
        """Test that 11-char hex strings are rejected (need exactly 12)."""
        info = {"hostname": "homevolt-68b6b34e70a.local"}  # 11 chars
        assert extract_mdns_id(info) is None

    def test_empty_dict(self) -> None:
        """Test returns None for empty dict."""
        assert extract_mdns_id({}) is None


class TestExtractMac:
    """Tests for extract_mac function."""

    def test_dict_with_deviceid(self) -> None:
        """Test extracting MAC from properties deviceid."""
        info = {"properties": {"deviceid": "AA:BB:CC:DD:EE:FF"}}
        assert extract_mac(info) == "aa:bb:cc:dd:ee:ff"

    def test_dict_with_bytes_deviceid(self) -> None:
        """Test extracting MAC from bytes deviceid."""
        info = {"properties": {b"deviceid": b"AABBCCDDEEFF"}}
        assert extract_mac(info) == "aa:bb:cc:dd:ee:ff"

    def test_dict_without_deviceid(self) -> None:
        """Test returns None when deviceid not present."""
        info = {"properties": {"other": "value"}}
        assert extract_mac(info) is None

    def test_dict_without_properties(self) -> None:
        """Test returns None when properties not present."""
        info = {"host": "192.168.1.100"}
        assert extract_mac(info) is None

    def test_dict_with_none_properties(self) -> None:
        """Test returns None when properties is None."""
        info = {"properties": None}
        assert extract_mac(info) is None

    def test_invalid_mac_format(self) -> None:
        """Test returns normalized value even for non-standard MAC format.

        Note: format_mac from HA normalizes the string but doesn't validate
        it's a real MAC address, so this returns the normalized input.
        """
        info = {"properties": {"deviceid": "not-a-mac"}}
        # format_mac doesn't validate, just normalizes
        assert extract_mac(info) == "not-a-mac"
