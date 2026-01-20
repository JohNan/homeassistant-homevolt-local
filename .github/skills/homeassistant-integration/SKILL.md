---
name: homeassistant-integration
description: Home Assistant custom integration development patterns, best practices, and conventions. Use when creating or modifying entities, config flows, coordinators, or any Home Assistant integration code.
---

# Home Assistant Custom Integration Development

This skill provides knowledge for developing Home Assistant custom integrations following best practices.

## Project Structure

```
custom_components/homevolt_local/
├── __init__.py          # Entry point with async_setup_entry
├── manifest.json        # Integration metadata and dependencies
├── const.py             # Domain and constants
├── config_flow.py       # UI configuration flow
├── coordinator.py       # Data update coordinator
├── models.py            # Data models
├── sensor.py            # Sensor platform
├── strings.json         # User-facing text and translations
├── services.yaml        # Service definitions (if applicable)
└── translations/        # Language translations

tests/                   # Integration tests (at repo root)
├── conftest.py          # Shared pytest fixtures
└── test_*.py            # Test files
```

## Core Patterns

### Entity Development

```python
class MySensor(CoordinatorEntity, SensorEntity):
    """Sensor entity using coordinator pattern."""

    _attr_has_entity_name = True  # Required for proper naming

    def __init__(self, coordinator: MyCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_sensor_name"
        self._attr_translation_key = "sensor_name"  # Use translations
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name="Device Name",
            manufacturer="Manufacturer",
            model="Model",
        )

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        return self.coordinator.data.some_value
```

### Coordinator Pattern

```python
class MyCoordinator(DataUpdateCoordinator[MyData]):
    """Data update coordinator."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )
        self.config_entry = config_entry

    async def _async_update_data(self) -> MyData:
        """Fetch data from API."""
        try:
            return await self._fetch_data()
        except ApiConnectionError as err:
            raise UpdateFailed(f"Connection error: {err}") from err
        except ApiAuthError as err:
            raise ConfigEntryAuthFailed(f"Auth error: {err}") from err
```

### Config Flow

```python
class MyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            else:
                await self.async_set_unique_id(info["unique_id"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=SCHEMA,
            errors=errors,
        )
```

## Sensor Classifications

### Power Sensors
```python
_attr_device_class = SensorDeviceClass.POWER
_attr_native_unit_of_measurement = UnitOfPower.WATT
_attr_state_class = SensorStateClass.MEASUREMENT
_attr_suggested_display_precision = 0
```

### Energy Sensors (Total Increasing)
```python
_attr_device_class = SensorDeviceClass.ENERGY
_attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
_attr_state_class = SensorStateClass.TOTAL_INCREASING
_attr_suggested_display_precision = 2
```

### Battery Percentage
```python
_attr_device_class = SensorDeviceClass.BATTERY
_attr_native_unit_of_measurement = PERCENTAGE
_attr_state_class = SensorStateClass.MEASUREMENT
```

## Common Anti-Patterns to Avoid

```python
# ❌ Blocking operations in event loop
data = requests.get(url)  # Blocks event loop

# ❌ Missing error handling
data = await self.api.get_data()  # No exception handling

# ❌ Hardcoded strings
self._attr_name = "Temperature"  # Not translatable

# ❌ Missing unique_id
# Entity without unique_id cannot be managed in UI
```

## Correct Patterns

```python
# ✅ Async operations
data = await hass.async_add_executor_job(requests.get, url)

# ✅ Proper error handling
try:
    data = await self.api.get_data()
except ApiException as err:
    raise UpdateFailed(f"API error: {err}") from err

# ✅ Translatable entity names
_attr_translation_key = "temperature"

# ✅ Always set unique_id
self._attr_unique_id = f"{entry_id}_temperature"
```

## Testing Patterns

```python
@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return the default mocked config entry."""
    return MockConfigEntry(
        title="Test Device",
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.100"},
        unique_id="device_unique_id",
    )

async def test_sensor_value(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test sensor returns correct value."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.device_power")
    assert state is not None
    assert state.state == "1500"
```

## Error Handling

| Exception | When to Use |
|-----------|-------------|
| `ConfigEntryNotReady` | Temporary setup failure (network issue) |
| `ConfigEntryAuthFailed` | Authentication/authorization failure |
| `UpdateFailed` | Coordinator update error |

## Resources

- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [Integration Quality Scale](https://developers.home-assistant.io/docs/integration_quality_scale_index)
- [HACS Documentation](https://hacs.xyz/)
