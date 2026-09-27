"""Tests for the Bbox sensor platform."""

from unittest.mock import AsyncMock

import homeassistant.helpers.device_registry as dr
import homeassistant.helpers.entity_registry as er
import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfDataRate, UnitOfInformation
from homeassistant.core import HomeAssistant, State

from types import SimpleNamespace
from typing import Any

from custom_components.livebox.const import DOMAIN
from custom_components.livebox.coordinator import LiveboxDataUpdateCoordinator
from custom_components.livebox.sensor import (
    SENSOR_TYPES,
    LiveboxSensor,
    LiveboxSensorEntityDescription,
)

from .helpers import load_fixture


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

    if AIOSysbus.__model in ["7"]:
        state = er.async_get(hass).async_get("sensor.pc_408_downlink_rate")
        assert state is not None
        state = er.async_get(hass).async_get("sensor.pc_408_uplink_rate")
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


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_last_reboot_reason_sensor(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock,
):
    """The reason comes from the previous session, the dates from the current one."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_last_reboot_reason")
    assert state is not None
    assert state.state == "TR069 reboot"
    assert state.attributes["Boot date"] == "2026-09-16T01:08:18Z"
    assert state.attributes["Boot reason"] == "NMC"
    assert state.attributes["Shutdown date"] == "2026-09-16T01:07:24Z"
    assert state.attributes["Boot counter"] == 134
    assert state.attributes["Watchdog reboot counter"] == 3
    assert state.attributes["Reboots since last upgrade"] == 85


@pytest.mark.parametrize("AIOSysbus", ["7", "7.1", "7.2"], indirect=True)
async def test_rate_sensors_match_issue_258_diagnostics(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock,
) -> None:
    """Test dynamic rate sensors keep distinct values from issue #258."""
    fixture = load_fixture("issue_258_livebox_nautilus_diagnostics_sanitized.json")
    stats = fixture["data"]["data"]["stats"]
    # The issue only provides the computed rates: rebuild the HomeLan
    # counters (bits over 30 seconds) the coordinator derives them from.
    AIOSysbus.homelan.async_get_interface.return_value = {
        "status": {
            item["friendly_name"]: {"Name": name, "FriendlyName": item["friendly_name"]}
            for name, item in stats.items()
        }
    }
    AIOSysbus.homelan.async_get_results.return_value = {
        "status": {
            item["friendly_name"]: {
                "Traffic": [
                    {
                        "Rx_Counter": item["rate_rx"] * 30_000_000,
                        "Tx_Counter": item["rate_tx"] * 30_000_000,
                    }
                ]
            }
            for item in stats.values()
        }
    }

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    unique_id = config_entry.runtime_data.unique_id

    def _value(key: str) -> float:
        entity_id = entity_registry.async_get_entity_id(
            "sensor", DOMAIN, f"{unique_id}_{key}"
        )
        assert entity_id is not None, key
        state = hass.states.get(entity_id)
        assert state is not None, key
        return float(state.state)

    assert _value("vap5g0priv_rate_rx") == 0.01
    assert _value("vap5g0priv_rate_tx") == 0.06
    assert _value("ETH0_rate_rx") == 0.01
    assert _value("ETH0_rate_tx") == 0.0


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


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_device_metric_sensors_are_created_for_wifi_clients(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock,
) -> None:
    """Test per-device Wi-Fi sensors expose the expected metrics."""
    AIOSysbus.__devices["status"].append(
        {
            "Key": "AA:BB:CC:DD:EE:FF",
            "Name": "Test device",
            "PhysAddress": "AA:BB:CC:DD:EE:FF",
            "Active": True,
            "Tags": "lan edev mac physical wifi ipv4 ipv6 dhcp events",
            "InterfaceName": "vap5g0priv0",
            "SignalStrength": -41,
            "SignalNoiseRatio": 32,
            "LastDataDownlinkRate": 7777,
            "LastDataUplinkRate": 8888,
        }
    )
    wlanvap = AIOSysbus.api_raw["NeMo.async_get_MIBs::lan"]["status"]["wlanvap"]
    wlanvap["vap5g0priv0"]["AssociatedDevice"]["AA:BB:CC:DD:EE:FF"] = {
        "MACAddress": "AA:BB:CC:DD:EE:FF",
        "TxBytes": 321,
        "RxBytes": 654,
    }

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)

    def _state(key: str) -> State:
        entity_id = entity_registry.async_get_entity_id(
            "sensor", DOMAIN, f"{config_entry.runtime_data.unique_id}_{key}"
        )
        assert entity_id is not None, key
        state = hass.states.get(entity_id)
        assert state is not None, key
        return state

    downlink = _state("aa_bb_cc_dd_ee_ff_downlink_rate")
    assert float(downlink.state) == 7.777
    assert downlink.attributes["unit_of_measurement"] == (
        UnitOfDataRate.MEGABITS_PER_SECOND
    )
    assert float(_state("aa_bb_cc_dd_ee_ff_uplink_rate").state) == 8.888
    tx_bytes = _state("aa_bb_cc_dd_ee_ff_tx_bytes")
    assert float(tx_bytes.state) == 0.000321
    assert tx_bytes.attributes["unit_of_measurement"] == UnitOfInformation.MEGABYTES
    assert float(_state("aa_bb_cc_dd_ee_ff_rx_bytes").state) == 0.000654
    assert float(_state("aa_bb_cc_dd_ee_ff_signal_strength").state) == -41
    assert float(_state("aa_bb_cc_dd_ee_ff_signal_noise_ratio").state) == 32
    assert downlink.attributes["friendly_name"] == "Test device Downlink Rate"

    entry = entity_registry.async_get(downlink.entity_id)
    assert entry is not None and entry.device_id is not None
    device = device_registry.async_get(entry.device_id)
    assert device is not None
    assert device.identifiers == {(DOMAIN, "AA:BB:CC:DD:EE:FF")}


def test_fiber_rate_attributes_use_gigabits_per_second() -> None:
    """Fiber status rate attributes should match their Gbit/s labels."""
    data = {
        "fiber_status": {
            "DownstreamMaxRate": 2488320,
            "DownstreamCurrRate": 2488320,
            "UpstreamMaxRate": 1244160,
            "UpstreamCurrRate": 1244160,
            "MaxBitRateSupported": 10000,
        }
    }

    rx_description = next(
        description
        for description in SENSOR_TYPES
        if description.key == "fiber_power_rx"
    )
    tx_description = next(
        description
        for description in SENSOR_TYPES
        if description.key == "fiber_power_tx"
    )

    assert rx_description.attrs is not None
    assert tx_description.attrs is not None
    assert rx_description.attrs["Downstream max rate Gbps"](data) == 2.48832
    assert rx_description.attrs["Downstream current rate Gbps"](data) == 2.48832
    assert rx_description.attrs["Max bitrate (Gbps)"](data) == 10
    assert tx_description.attrs["Upstream max rate (Gbps)"](data) == 1.24416
    assert tx_description.attrs["Upstream current rate (Gbps)"](data) == 1.24416
    assert tx_description.attrs["Max bitrate (Gbps)"](data) == 10
