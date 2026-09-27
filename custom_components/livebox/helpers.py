"""Helpers functions."""

from collections.abc import Mapping
from typing import Any

from .const import CONF_DISPLAY_DEVICES, DEFAULT_DISPLAY_DEVICES

# Legacy option value kept by older installs after the selector was renamed.
_LEGACY_DISPLAY_DEVICES = {"Active only": "Active"}


def normalize_display_devices(value: str | None) -> str:
    """Normalize legacy device_tracker_mode values to current selector options."""
    if value is None:
        return DEFAULT_DISPLAY_DEVICES
    return _LEGACY_DISPLAY_DEVICES.get(value, value)


def normalize_options(options: Mapping[str, Any]) -> dict[str, Any]:
    """Return options with legacy values migrated to current ones."""
    normalized = dict(options)
    current = normalized.get(CONF_DISPLAY_DEVICES)
    if current in _LEGACY_DISPLAY_DEVICES:
        normalized[CONF_DISPLAY_DEVICES] = _LEGACY_DISPLAY_DEVICES[current]
    return normalized


def find_item(data: dict[str, Any], key_chain: str, default: Any = None) -> Any:
    """Get recursive key and return value.

    Parameters:
        data (dict[str, Any]) : dictionary to search
        key (str): searched string with dot for key delimited (ex: "key.key.key")
            It is possible to integrate an element of an array
            by indicating its index number
        default (Any): default value to return if key not found
    Returns:
        Any: value of the key or default if not found
    Example:
        >>> find_item({"a": {"b": [{"c": "value_a"},{"d": "value_b"}]}}, "a.b.0.c")
        "value_a"
        >>> find_item({"a": {"b": [{"c": "value"}]}}, "a.b.1.c", "default")
        "default"
    """
    current: Any = data
    if (keys := key_chain.split(".")) and isinstance(keys, list):
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            elif (
                isinstance(current, list)
                and len(current) > 0
                and key.isdigit()
                and int(key) < len(current)
            ):
                current = current[int(key)]
    return default if current is None and default is not None else current
