# GitHub Copilot & Claude Code Instructions

This repository contains a **Home Assistant Custom Integration** for Homevolt Local devices. It follows the patterns and conventions from Home Assistant Core but is structured as a HACS-compatible custom component.

## Custom Integration Structure

```
custom_components/homevolt_local/
├── __init__.py          # Entry point with async_setup_entry
├── manifest.json        # Integration metadata and dependencies
├── const.py             # Domain and constants
├── config_flow.py       # UI configuration flow
├── coordinator.py       # Data update coordinator (if present)
├── models.py            # Data models
├── sensor.py            # Sensor platform
├── strings.json         # User-facing text and translations
├── services.yaml        # Service definitions (if applicable)
└── translations/        # Language translations

tests/                   # Integration tests (at repo root)
├── __init__.py
├── conftest.py          # Shared pytest fixtures
├── test_config_flow.py
├── test_coordinator.py
├── test_init.py
├── test_models.py
└── test_sensor.py
```

## Development Commands

### Install Dependencies

```bash
pip install -r requirements-dev.txt
```

### Run Tests

```bash
PYTHONPATH=. pytest
```

### Run Tests with Coverage

```bash
PYTHONPATH=. pytest --cov=custom_components/homevolt_local --cov-report=term-missing
```

### Run Linting

```bash
ruff check custom_components/
ruff format custom_components/
```

### Type Checking

```bash
mypy custom_components/homevolt_local
```

## Code Quality Standards

- **Formatting**: Ruff
- **Linting**: Ruff
- **Type Checking**: MyPy
- **Testing**: pytest with fixtures
- **Coverage**: Aim for high test coverage

## Python Requirements

- **Compatibility**: Python 3.12+
- **Async**: All external I/O operations must be async
- **Type Hints**: Add type hints to all functions and methods

## Integration Guidelines

### Configuration Flow
- **UI Setup Required**: Configuration via UI using config flow
- **Unique ID**: Every config entry should have a unique ID
- **Error Handling**: Define errors in `strings.json` under `config.error`

### Entity Development
- **Unique IDs**: Every entity must have a unique ID
- **Entity Naming**: Use `_attr_has_entity_name = True`
- **Device Info**: Group entities under devices with proper metadata
- **Translations**: Use translation keys for entity names

### Async Programming
- All external I/O operations must be async
- Use `async_add_executor_job` for blocking operations
- Never block the event loop

### Error Handling
- Use `ConfigEntryNotReady` for temporary setup failures
- Use `ConfigEntryAuthFailed` for authentication issues
- Use `UpdateFailed` for coordinator update errors

## Testing Requirements

- **Location**: `tests/` (at repo root)
- **Framework**: pytest with `pytest-homeassistant-custom-component`
- **Mocking**: Mock all external dependencies
- **Coverage**: Test config flows, coordinators, and entities

### Test Patterns

```python
@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return the default mocked config entry."""
    return MockConfigEntry(
        title="Homevolt",
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.100"},
        unique_id="device_unique_id",
    )
```

## Key Differences from Home Assistant Core

1. **File Location**: Code lives in `custom_components/` not `homeassistant/components/`
2. **Test Location**: Tests are in `tests/` at repo root (like HACS integration pattern)
3. **PYTHONPATH**: Must set `PYTHONPATH=.` when running tests
4. **No hassfest**: Custom integrations don't use the hassfest validation script
5. **HACS Compatible**: Includes `hacs.json` for HACS integration

## Common Anti-Patterns to Avoid

```python
# ❌ Blocking operations in event loop
data = requests.get(url)  # Blocks event loop

# ❌ Missing error handling
data = await self.api.get_data()  # No exception handling

# ❌ Hardcoded strings
self._attr_name = "Temperature"  # Not translatable
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
```

## Resources

- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [Integration Quality Scale](https://developers.home-assistant.io/docs/integration_quality_scale_index)
- [HACS Documentation](https://hacs.xyz/)
