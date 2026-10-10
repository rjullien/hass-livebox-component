# Orange Livebox Router

[![GitHub release](https://img.shields.io/github/v/release/rjullien/hass-livebox-component?style=for-the-badge)](https://github.com/rjullien/hass-livebox-component/releases)
[![GitHub Activity](https://img.shields.io/github/commit-activity/y/rjullien/hass-livebox-component?style=for-the-badge)](https://github.com/rjullien/hass-livebox-component/commits/master)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://hacs.xyz)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2025.5.0%2B-blue?style=for-the-badge)](https://www.home-assistant.io/)

Custom component for [Home Assistant](https://www.home-assistant.io/) to observe and control [Orange Livebox](http://www.orange.fr/) routers.

> **Fork status:** Aligned with upstream [cyr-ius/hass-livebox-component](https://github.com/cyr-ius/hass-livebox-component) **v2.6.0** (commit `30c75a0`), fork release **2.6.0.3**. Fork-specific safeguards are preserved; cosmetic-only deviations from upstream are avoided.
>
> **Versioning:** `X.Y.Z.N` — `X.Y.Z` = upstream base, `N` = fork revision (e.g. `2.6.0.1` = upstream 2.6.0, fork rev 1).
>
> **HACS:** use repository `rjullien/hass-livebox-component` (not `cyr-ius/hass-livebox-component`) to get this fork.

## Requirements

|                    | Minimum (runtime)               | Tested in CI      |
| ------------------ | ------------------------------- | ----------------- |
| **Home Assistant** | **2025.5.0**                    | 2026.7.2          |
| **Python**         | _(bundled with HA — see below)_ | 3.14.2 (dev only) |
| **aiosysbus**      | **1.2.5**                       | 1.2.5             |

### Minimum Home Assistant version

**2025.5.0** — declared by upstream in `hacs.json`, consistent with the code:

- `AddConfigEntryEntitiesCallback` (calendar platform) exists since HA **2025.3.0**
- `async_step_reconfigure` (config flow) exists since HA **2024.12**
- upstream bumped the declared minimum from `2024.1.0` → `2025.5.0` in Oct 2025

The fork does not introduce APIs that require a version above 2025.5.0.

### Python — what users actually need

You do **not** install Python for this integration. Home Assistant Core ships its own Python runtime.

| Your Home Assistant version | Python bundled by HA Core |
| --------------------------- | ------------------------- |
| 2025.5.0 – 2026.2.x         | **3.13.2+**               |
| 2026.3.0 and newer          | **3.14.2+**               |

So with the declared minimum **HA 2025.5.0**, you need a HA install that already runs on **Python 3.13.2+** (OS / Container / Supervised — HA handles this).

**Python 3.14.2** in `pyproject.toml` applies only to **local development** (`uv sync`, pytest, lint) — not to end users installing via HACS.

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

> Do **not** use `cyr-ius/hass-livebox-component` if you want this fork (session management, multi-box fixes).

### Initial setup

You must have set a password for your Livebox router web administration page.

On first connection, Home Assistant asks for the Livebox password.

### Options

Use **Configure** on the integration to change:

- **Wired tracking** (default: No)
- **Wireless tracking** (default: Yes)
- **Timeout tracking** (default: 300 s): delay before a device is considered away
- **Track devices** (default: Active): All or Active

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

### 2.6.0.4

- Session logout now uses the web UI method (`X-Sah-Logout` + `releaseContext`); `/logout.cmd` returned 404 on Livebox Fibre

### 2.6.0.3

- Realign cosmetic hunks with upstream
- Call-log calendar realigned with upstream (30-day pruning removed)
- Rolling 32-bit counters realigned with upstream (per-entity state removed)
- Session credentials are written to storage only when they change, not on every poll
- Fibre guest Wi-Fi controls realigned with upstream; pinned aiosysbus handles timer calls
- Unknown ProductClass warning removed to match upstream

### 2.6.0.2

- Replace the deprecated device-registry lookup for repeater parents while retaining compatibility with HA 2025.5
- Restore fork safeguard coverage using upstream-style AIOSysbus integration setup tests
- Rebuild the repeater topology (`buildTopology`) only once a day when no repeater is detected (5 min otherwise), and rate-limit retries after a failed topology query instead of retrying every minute

### 2.6.0.1

- Rebase fork history onto upstream **v2.6.0** (`30c75a0`) so GitHub Compare / ForkUpstreamMonitor report `behind_by=0`
- Take upstream 2.6.0: `aiosysbus` 1.2.5, `wifi_bridge` client tracking, repeater topology refresh for roaming clients, ethernet reporting on ETH* interfaces, last reboot reason sensor, HA 2026.12 reconfigure listener fix, AIOSysbus-driven test suite
- Keep upstream `Funbox6` model mapping alongside the fork's unknown-ProductClass fallback warning
- Upstream test guidelines (`AGENTS.md`) adopted; upstream's rewritten test suite kept, fork rolling-counter regression tests preserved
- Preserve fork safeguards: session logout/persistence, multi-box rolling counters, WAN access unique_id / override, Fibre guest Wi‑Fi helpers, `via_device` registry re-link

### 2.5.6.1

- Rebase fork history onto upstream **v2.5.6** (`f1fe858`) so GitHub Compare / ForkUpstreamMonitor report `behind_by=0` (identical tree; no `2.5.6.2`)
- Align with upstream **v2.5.6**; keep `X.Y.Z.N` versioning (`2.5.6` + fork rev 1)
- Take upstream recorder fix: drop high-churn `uptime` attribute from WAN connectivity binary sensor (dedicated uptime sensor remains)
- Take upstream `ScannerEntity` import path fix (`device_tracker.entity`)
- Tooling: `actions/stale` v11, `actions/setup-python` v7, ruff `v0.16.2`, codespell `v2.4.3` (keep fork Python 3.14 / HA 2026.7.2 CI stack and `rjullien` workflow guards)
- Keep ruff `target-version = "py313"` so format/check do not emit Python 3.14-only `except A, B` syntax (breaks HA 2025.5 / Python 3.13)
- Preserve fork safeguards: session logout/persistence, multi-box rolling counters, WAN access unique_id / override, Fibre guest Wi‑Fi helpers, `via_device` registry re-link

### 2.5.4.3

- Rebase onto upstream v2.5.4 (`43bc16b`); keep `X.Y.Z.N` versioning (`2.5.4` + fork rev 3)
- Restore Fibre guest Wi-Fi helpers and `via_device` registry re-link after rebase
- Ensure parent repeater exists before client `via_device` update
- Migrate legacy `Active only` → `Active` in setup and options flow
- Fix `async_get_callers` exception syntax (`except (ValueError, TypeError)`)

### 2.5.4.2

- Modernize dev stack: Python 3.14.2, Home Assistant 2026.7.2, pytest-hacc 0.13.346
- Fix CI lockfile (PyYAML / aiosysbus compatibility)
- Adopt 4-part versioning (`upstream.fork`)
- Update HACS minimum HA version documentation (runtime min: 2025.5.0, CI: 2026.7.2)

### 2.5.4.1

- Merge upstream v2.5.4 while keeping fork fixes:
  - Session logout/persistence (prevent Livebox session exhaustion)
  - Per-instance rolling 32-bit counters for multi-box setups
  - WAN access unique_id migration (#287)
  - Guest WiFi turn_off fix for Livebox Fibre
  - Reconfigure flow, device sensors, eth interfaces (from upstream)

## Known issues (accepted)

### Call-log calendar cache

`LiveboxCallLogCalendar._calls` grows until the Livebox reboots. The impact is
negligible (a few hundred bytes per call), the cache is cleared on reboot, and
the owner's line receives practically no calls. The 30-day pruning was removed
in 2.6.0.3 to avoid diverging from upstream; do not re-add it.

### Rolling 32-bit counters

Rolling counter state is shared across config entries, so totals can be wrong
when two or more Liveboxes are configured in the same Home Assistant. The owner
has one Livebox, so this is accepted to avoid diverging from upstream.

### Unknown Livebox ProductClass

An unrecognized `ProductClass` leaves `model` unset without a warning. This is
accepted to stay aligned with upstream.
