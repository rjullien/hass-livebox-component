# Orange Livebox Router

[![GitHub release](https://img.shields.io/github/v/release/rjullien/hass-livebox-component?style=for-the-badge)](https://github.com/rjullien/hass-livebox-component/releases)
[![GitHub Activity](https://img.shields.io/github/commit-activity/y/rjullien/hass-livebox-component?style=for-the-badge)](https://github.com/rjullien/hass-livebox-component/commits/master)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://hacs.xyz)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.7.2%2B-blue?style=for-the-badge)](https://www.home-assistant.io/)

Custom component for [Home Assistant](https://www.home-assistant.io/) to observe and control [Orange Livebox](http://www.orange.fr/) routers.

> **Fork status:** Aligned with upstream [cyr-ius/hass-livebox-component](https://github.com/cyr-ius/hass-livebox-component) **v2.5.4** (commit `4a817d5`, 2026-06-29). Fork-specific improvements (session logout/persistence, multi-box counters, WAN access fixes, guest WiFi fix) are preserved on top.
>
> **Versioning:** `X.Y.Z.N` — `X.Y.Z` = upstream base, `N` = fork revision (e.g. `2.5.4.2` = upstream 2.5.4, fork rev 2).
>
> **HACS:** use repository `rjullien/hass-livebox-component` (not `cyr-ius/hass-livebox-component`) to get this fork.

## Requirements

| Component           | Minimum version |
| ------------------- | --------------- |
| Home Assistant      | **2026.7.2**    |
| Python (dev only)   | **3.14.2**      |
| aiosysbus (runtime) | **1.2.4**       |

The dev/test stack targets Home Assistant **2026.7.2** (see `uv.lock`). Older HA versions are not validated by CI.

## Supported features

- Sensor with traffic metrics
- Binary sensor: WAN status, public IP, private IP
- Device tracker for connected devices (optional wired tracking)
- Switch: enable/disable wireless and guest WiFi
- Button: restart box, ring phone, clear calls
- Calendar: missed calls
- Config flow reconfigure (change credentials without re-adding)

## Installation

### HACS (this fork)

Add the custom repository in HACS:

`https://github.com/rjullien/hass-livebox-component`

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=rjullien&repository=hass-livebox-component&category=integration)

Then add the integration:

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=livebox)

> Do **not** use `cyr-ius/hass-livebox-component` if you want this fork (session management, multi-box fixes, HA 2026.7.2 validation).

### Initial setup

You must have set a password for your Livebox router web administration page.

On first connection, Home Assistant asks for the Livebox password.

### Options

Use **Configure** on the integration to change:

- **Wired tracking** (default: No)
- **Wireless tracking** (default: Yes)
- **Timeout tracking** (default: 300 s): delay before a device is considered away
- **Track devices** (default: Active): All or Active only

## Supported routers

Only routers with Livebox OS:

- Livebox 3, 4, 5, 6, 7, W7
- Livebox Nautilus (Arcadyan)
- KPN Box 12 (Firmware: V12.C.23.04.36)
- Sagemcom f@st 5656

### Unsupported routers

Despite the "Livebox" label, these models **cannot** be supported:

- Arcadyan PRV3399 ([Livebox Plus](https://ayuda.orange.es/dispositivos-y-routers/2381-router-livebox-plus))
- Arcadyan ERV33AX349B-LT ([Livebox 6+](https://ayuda.orange.es/dispositivos-y-routers/2755-router-livebox-6plus))
- ZTE ZTEGLB7xxxxxx ([Livebox 7 ZTE](https://ayuda.orange.es/dispositivos-y-routers/3220-router-livebox-7))

## Presence detection

Tracks devices connected to the Livebox. Can be disabled in integration options.

The Livebox waits ~1–2 minutes before marking a device inactive. New connections are reported almost immediately.

## Development

Requires Python **3.14.2+** and [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync --group dev
uv run pytest
uv run prek run --all-files
```

CI runs on Python 3.14 with Home Assistant **2026.7.2** (via `pytest-homeassistant-custom-component`).

## Upstream

Original project: [cyr-ius/hass-livebox-component](https://github.com/cyr-ius/hass-livebox-component)

Report fork-specific issues on [rjullien/hass-livebox-component/issues](https://github.com/rjullien/hass-livebox-component/issues).

## Changelog (fork)

### 2.5.4.2

- Modernize dev stack: Python 3.14.2, Home Assistant 2026.7.2, pytest-hacc 0.13.346
- Fix CI lockfile (PyYAML / aiosysbus compatibility)
- Adopt 4-part versioning (`upstream.fork`)
- Update HACS minimum HA version to 2026.7.2

### 2.5.4.1

- Merge upstream v2.5.4 while keeping fork fixes:
  - Session logout/persistence (prevent Livebox session exhaustion)
  - Per-instance rolling 32-bit counters for multi-box setups
  - WAN access unique_id migration (#287)
  - Guest WiFi turn_off fix for Livebox Fibre
  - Reconfigure flow, device sensors, eth interfaces (from upstream)
