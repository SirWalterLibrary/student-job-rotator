"""Configuration loaded from environment variables, with optional overrides."""
import os


def _flag(value) -> bool:
    """Interpret a config value as a boolean (only 1/true count as true)."""
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true")


def _value(overrides: dict, key: str, default: str) -> str:
    """Return the override for key if present, else the env var, else default."""
    if key in overrides:
        return str(overrides[key])
    return os.environ.get(key, default)


def load_config(overrides: dict | None = None) -> dict:
    """Build the config dict from env vars, applying any in-memory overrides."""
    overrides = overrides or {}
    return {
        "DATA_DIR": _value(overrides, "DATA_DIR", "./data"),
        "ADMIN_PIN": _value(overrides, "ADMIN_PIN", ""),
        "APP_ENV": _value(overrides, "APP_ENV", "development"),
        "ALLOW_TODAY_OVERRIDE": _flag(_value(overrides, "ALLOW_TODAY_OVERRIDE", "0")),
        "TRUST_PROXY": _flag(_value(overrides, "TRUST_PROXY", "0")),
    }
