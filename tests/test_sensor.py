"""Tests for the Bbox sensor platform."""

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import homeassistant.helpers.entity_registry as er
import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pytest_homeassistant_custom_component.common import load_json_object_fixture

from custom_components.livebox.coordinator import LiveboxDataUpdateCoordinator
from custom_components.livebox.sensor import (
    LiveboxSensor,
    LiveboxSensorEntityDescription,
    async_setup_entry,
)


def _load_fixture(name: str) -> dict[str, Any]:
    """Load a typed test fixture."""
    return cast(dict[str, Any], load_json_object_fixture(name))


@pytest.mark.parametrize("AIOSysbus", ["3", "5", "7", "7.1", "7.2"], indirect=True)
async def test_sensors_state(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock,
):
    """Test the state of various sensors."""
    # Setup the integration
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_fiber_power_tx")
    assert state is not None
    state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_fiber_power_rx")
    assert state is not None

    state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_fiber_tx")
    assert state is not None
    state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_fiber_rx")
    assert state is not None

    state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_callers")
    assert state is not None

    if AIOSysbus.__model in ["7.1"]:
        state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_eth2_rate_rx")
        assert state is not None
        assert float(state.state) >= 0
        state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_eth2_rate_tx")
        assert state is not None
        assert float(state.state) >= 0

    # entity_registry_enabled_default=False
    state = er.async_get(hass).async_get(f"sensor.{AIOSysbus.__unique_name}_wifi_tx")
    assert state is not None
    state = er.async_get(hass).async_get(f"sensor.{AIOSysbus.__unique_name}_wifi_rx")
    assert state is not None
    state = er.async_get(hass).async_get(
        f"sensor.{AIOSysbus.__unique_name}_ports_forwarding"
    )
    assert state is not None
    state = er.async_get(hass).async_get(
        f"sensor.{AIOSysbus.__unique_name}_dhcp_leases"
    )
    assert state is not None
    state = er.async_get(hass).async_get(
        f"sensor.{AIOSysbus.__unique_name}_guest_dhcp_leases"
    )
    assert state is not None


async def test_rate_sensors_match_issue_258_diagnostics(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> None:
    """Test dynamic rate sensors keep distinct values from issue #258."""
    fixture = _load_fixture("issue_258_livebox_nautilus_diagnostics_sanitized.json")

    coordinator = LiveboxDataUpdateCoordinator(hass, config_entry)
    coordinator.unique_id = "issue258"
    coordinator.data = fixture["data"]["data"]
    config_entry.runtime_data = coordinator

    entities: list[LiveboxSensor] = []

    def _add_entities(
        new_entities: list[LiveboxSensor], update_before_add: bool = False
    ) -> None:
        del update_before_add
        entities.extend(new_entities)

    await async_setup_entry(
        hass, config_entry, cast(AddEntitiesCallback, _add_entities)
    )

    sensors = {entity.entity_description.key: entity for entity in entities}

    assert sensors["vap5g0priv_rate_rx"].native_value == 0.01
    assert sensors["vap5g0priv_rate_tx"].native_value == 0.06
    assert sensors["ETH0_rate_rx"].native_value == 0.01
    assert sensors["ETH0_rate_tx"].native_value == 0.0


@pytest.mark.parametrize("AIOSysbus", ["7.1"], indirect=True)
async def test_rate_sensors_use_megabits_per_second_math(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock,
) -> None:
    """Test rate sensors use Mbit/s math to match their declared unit."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    rx_state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_eth2_rate_rx")
    assert rx_state is not None
    assert float(rx_state.state) == 0.01

    tx_state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_eth2_rate_tx")
    assert tx_state is not None
    assert float(tx_state.state) == 5.69


def _make_rolling_sensor(
    data: dict[str, Any],
    rolling_data_path: str,
    coordinator_unique_id: str = "test_box",
) -> LiveboxSensor:
    """Build a minimal LiveboxSensor wired to a stub coordinator."""
    coordinator = object.__new__(LiveboxDataUpdateCoordinator)
    coordinator.unique_id = coordinator_unique_id
    coordinator.data = data
    coordinator.config_entry = SimpleNamespace(
        data={"use_tls": False, "host": "192.168.1.1", "port": 80},
    )

    description = LiveboxSensorEntityDescription(
        key=f"test_{rolling_data_path.replace('.', '_')}",
        rolling_data_path=rolling_data_path,
    )

    sensor = object.__new__(LiveboxSensor)
    sensor.coordinator = coordinator
    sensor.entity_description = description
    sensor._rolling_prev_reading = 0
    sensor._rolling_prev_uptime = 0
    sensor._rolling_rolls = 0
    return sensor


def test_rolling_32bit_two_independent_instances_do_not_share_state() -> None:
    """Two LiveboxSensor instances must accumulate rollover independently.

    Regression guard for item 2a: previously `get_rolling_32_bit_value_fn` created
    module-level closures stored in SENSOR_TYPES. With two Livebox boxes configured,
    the same closure was reused, corrupting both counters. State must now live on
    the entity instance.
    """

    # Data scaffold: uptime + the counter path used by each sensor
    def _data(uptime: int, rx_bytes: int) -> dict[str, Any]:
        return {
            "infos": {"UpTime": uptime},
            "fiber_stats": {"RxBytes": rx_bytes},
        }

    sensor_box1 = _make_rolling_sensor(_data(100, 0), "fiber_stats.RxBytes", "box1")
    sensor_box2 = _make_rolling_sensor(_data(100, 0), "fiber_stats.RxBytes", "box2")

    # --- Simulate a near-rollover on box1 ---
    # Feed box1 a value just under 2^32
    high_value = (1 << 32) - 10
    sensor_box1.coordinator.data = _data(100, high_value)
    assert sensor_box1.native_value == high_value

    # --- box2 starts fresh and receives a small counter ---
    sensor_box2.coordinator.data = _data(100, 50)
    assert sensor_box2.native_value == 50  # must NOT be inflated by box1's roll count

    # --- Trigger the actual 32-bit rollover on box1 ---
    after_rollover = 5  # the counter wrapped: new reading is 5
    sensor_box1.coordinator.data = _data(110, after_rollover)
    box1_value = sensor_box1.native_value
    # After one roll: (1 << 32) + 5
    assert box1_value == (1 << 32) + after_rollover

    # --- box2 must be completely unaffected ---
    # It should see its own counter advancing normally with no roll offset
    sensor_box2.coordinator.data = _data(110, 100)
    box2_value = sensor_box2.native_value
    assert box2_value == 100  # no spurious roll inherited from box1
    assert box1_value != box2_value


def test_rolling_32bit_resets_on_router_reboot() -> None:
    """Rolling counter must reset to zero when uptime decreases (router reboot)."""

    def _data(uptime: int, rx_bytes: int) -> dict[str, Any]:
        return {
            "infos": {"UpTime": uptime},
            "wifi_stats": {"RxBytes": rx_bytes},
        }

    sensor = _make_rolling_sensor(_data(500, 1000), "wifi_stats.RxBytes")

    # Advance the counter normally
    sensor.coordinator.data = _data(500, 1000)
    assert sensor.native_value == 1000

    sensor.coordinator.data = _data(600, 2000)
    assert sensor.native_value == 2000

    # Simulate reboot: uptime dropped below previous
    sensor.coordinator.data = _data(10, 50)
    assert sensor.native_value == 50  # state reset; no carry-over from pre-reboot
    assert sensor._rolling_rolls == 0
    assert sensor._rolling_prev_reading == 50
