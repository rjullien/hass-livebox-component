"""Lightweight unit tests for Livebox device tracker topology updates."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

import pytest
from homeassistant.helpers.entity import EntityDescription

from custom_components.livebox.const import DOMAIN
from custom_components.livebox.coordinator import LiveboxDataUpdateCoordinator
from custom_components.livebox.device_tracker import LiveboxDeviceScannerEntity


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations() -> None:
    """Avoid pulling the Home Assistant test harness into pure unit tests."""


async def test_device_tracker_updates_via_device_on_coordinator_refresh() -> None:
    """Update via_device when topology appears on a later refresh."""
    coordinator = object.__new__(LiveboxDataUpdateCoordinator)
    coordinator.hass = cast(Any, SimpleNamespace())
    coordinator.unique_id = "LIVEBOX-1"
    coordinator.config_entry = SimpleNamespace(
        entry_id="entry-1",
        data={"host": "192.168.1.1", "port": 80},
        options={},
    )
    coordinator.data = {
        "infos": {"ProductClass": "Livebox 7"},
        "devices": {
            "DD:DD:DD:DD:DD:01": {
                "Key": "DD:DD:DD:DD:DD:01",
                "Name": "Device-Repeater-5g-1",
                "IPAddress": "192.168.1.21",
            }
        },
        "topology_repeaters": {},
        "topology_via_device": {},
    }

    entity = LiveboxDeviceScannerEntity(
        coordinator,
        EntityDescription(
            key="DD:DD:DD:DD:DD:01_tracker",
            name="Device-Repeater-5g-1",
        ),
        coordinator.data["devices"]["DD:DD:DD:DD:DD:01"],
    )
    entity.hass = coordinator.hass
    entity.async_write_ha_state = MagicMock()

    # Simulate a coordinator update where topology now shows via_device
    coordinator.data = {
        "infos": {"ProductClass": "Livebox 7"},
        "devices": {
            "DD:DD:DD:DD:DD:01": {
                "Key": "DD:DD:DD:DD:DD:01",
                "Name": "Device-Repeater-5g-1",
                "IPAddress": "192.168.1.99",
            }
        },
        "topology_repeaters": {"CC:CC:CC:CC:CC:01": "Repeater-1"},
        "topology_via_device": {"DD:DD:DD:DD:DD:01": "CC:CC:CC:CC:CC:01"},
    }

    entity._handle_coordinator_update()

    # IP should be updated
    assert entity._attr_ip_address == "192.168.1.99"
    # via_device should now reflect the repeater
    assert entity._via_device == (DOMAIN, "CC:CC:CC:CC:CC:01")
    # async_write_ha_state should have been called
    entity.async_write_ha_state.assert_called_once()
