import unittest
from unittest.mock import patch, AsyncMock, MagicMock

from custom_components.homevolt_local.config_flow import (
    is_valid_host,
    construct_resource_url,
    validate_host,
    InvalidAuth,
    CannotConnect,
    InvalidResource,
    DuplicateHost,
)

class TestConfigFlow(unittest.TestCase):
    def test_is_valid_host(self):
        """Test the is_valid_host function."""
        self.assertTrue(is_valid_host("192.168.1.1"))
        self.assertTrue(is_valid_host("homevolt.local"))
        self.assertFalse(is_valid_host(""))
        self.assertFalse(is_valid_host("invalid host"))

    def test_construct_resource_url(self):
        """Test the construct_resource_url function."""
        self.assertEqual(
            construct_resource_url("http://192.168.1.1"),
            "http://192.168.1.1/ems.json"
        )
        self.assertEqual(
            construct_resource_url("https://192.168.1.1"),
            "https://192.168.1.1/ems.json"
        )

    @patch('custom_components.homevolt_local.config_flow.async_get_clientsession')
    def test_validate_host(self, mock_get_session):
        """Test the validate_host function."""
        hass = MagicMock()

        async def run_test():
            # Mock the session and response
            mock_session = MagicMock()
            mock_response = AsyncMock()
            mock_response.status = 200

            # This is the key part for mocking the async context manager
            enter_mock = AsyncMock()
            enter_mock.json = AsyncMock(return_value={"aggregated": {}})
            enter_mock.status = 200

            mock_response.__aenter__.return_value = enter_mock

            mock_session.get.return_value = mock_response
            mock_get_session.return_value = mock_session

            # Test success
            result = await validate_host(hass, "http://192.168.1.1", "user", "pass")
            self.assertEqual(result["host"], "http://192.168.1.1")

            # Test InvalidAuth
            enter_mock.status = 401
            with self.assertRaises(InvalidAuth):
                await validate_host(hass, "http://192.168.1.1", "user", "pass")

            # Test CannotConnect
            enter_mock.status = 500
            with self.assertRaises(CannotConnect):
                await validate_host(hass, "http://192.168.1.1", "user", "pass")

            # Test InvalidResource for invalid host
            with self.assertRaises(InvalidResource):
                await validate_host(hass, "invalid host")

            # Test InvalidResource for missing protocol
            with self.assertRaises(InvalidResource):
                await validate_host(hass, "192.168.1.1")

            # Test DuplicateHost
            with self.assertRaises(DuplicateHost):
                await validate_host(hass, "http://192.168.1.1", existing_hosts=["http://192.168.1.1"])

        import asyncio
        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()
