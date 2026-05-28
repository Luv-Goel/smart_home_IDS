# Shared Configuration System

This is the centralized configuration system for the Smart Home IDS platform.

## Features
- **Pydantic Settings**: Fully typed configuration.
- **YAML configs**: Supports environment-specific configs via `environments/<env>.yaml`.
- **Environment Overrides**: Use environment variables to override any specific setting.
- **Hot Reloading**: Supports reading config values on-demand using `reload()`.
- **Secret Loading**: Loads secrets transparently from `.env` or Docker secrets (`/run/secrets`).
- **Edge Optimized**: Includes specific configuration parameters for Raspberry Pi (e.g. inference `num_threads`).

## Usage

### Using the configuration

```python
from shared.config import settings

print(settings.app.name)
print(settings.database.url)
```

### Changing Environments

Set the `APP_ENV` environment variable to switch environments:

```bash
export APP_ENV=edge
python my_script.py
```

### Environment Variable Overrides

Any value in the YAML configuration can be overridden by environment variables using the `__` nested delimiter.

```bash
export APP__LOG_LEVEL=DEBUG
export DATABASE__POOL_SIZE=20
```

### Secrets

Copy `.env.template` to `.env` in the root of the app that is running and fill it with real secrets. DO NOT commit the `.env` file to source control.

```bash
cp .env.template .env
```

### Hot Reload

If configuration variables change at runtime, you can call `reload()` to get a fresh configuration state.

```python
from shared.config import reload

new_settings = reload()
```
