# Fork safeguards for upstream syncs

This inventory was checked against `git diff 30c75a0..origin/master`, where
`30c75a0` is upstream v2.6.0 and `origin/master` is fork v2.6.0.2. The entries
below account for the fork's code, test, workflow, and tooling changes in that
comparison. Reasons are grounded in the fork changelog, commit history, linked
issues, or owner-provided operating context; anything not documented is marked
explicitly rather than inferred.

## Safeguard inventory

### 1. Persist, release, and recover Livebox sessions

- **What:** Persist each entry's session cookies, context ID, base URL, and TLS
  verification setting after successful polling. Log out when an entry unloads,
  and attempt to release a persisted orphan before setting up a new session.
  On a top-level `HttpRequestFailed`, clear the in-memory session token so the
  next polling cycle can authenticate again.
- **Why:** The Livebox has a limited session table. Orphaned sessions otherwise
  remain until timeout; repeated HA restarts/reloads can exhaust the table and
  make the API stop responding. This is documented by commit `f37b631` (issue
  #8) and the README fork changelog. Commit `fb7a9bc` documents why a stale
  token must be invalidated after a communication failure.
- **Where:** `session.py::LiveboxSessionStore` and
  `session.py::async_logout_session`; `coordinator.py::async_persist_session`,
  `coordinator.py::async_logout`, and
  `LiveboxDataUpdateCoordinator._async_update_data`;
  `__init__.py::_async_logout_orphaned_session`,
  `async_setup_entry`, and `async_unload_entry`.
- **Protecting tests:** `tests/test_session.py::test_logout_session_success_statuses`,
  `test_logout_session_verify_tls_false`, `test_logout_session_failure_status`,
  `test_logout_session_exception`, `test_logout_session_multiple_cookies`,
  `test_store_save_load_roundtrip`, `test_store_clear`,
  `test_store_verify_tls_default`, `test_unload_calls_logout`,
  `test_unload_no_runtime_data`, and `test_orphan_cleanup_on_boot`.
- **Merge pitfalls:** Keep storage scoped to the config entry and preserve the
  TLS setting for orphan logout. Stop platform polling before logging out on
  unload. Keep token invalidation in the top-level update failure path; the
  `f37b631` commit explains that clearing it for every endpoint failure can
  trigger a login storm during one polling cycle. The current tests do not
  directly assert `async_persist_session` or token invalidation after
  `HttpRequestFailed`; preserve those paths when changing coordinator error
  handling.

  **Operational note:** On René's real Livebox, startup can log
  `Failed to logout orphaned session (Livebox may be unreachable)`. This
  best-effort logout warning is harmless when data starts flowing immediately
  afterward; do not mistake the warning alone for a failed integration setup.

### 2. Keep rolling 32-bit counters independent

- **What:** Fiber and Wi-Fi byte counters accumulate across 32-bit wraparound.
  Previous reading, uptime, and wrap count live on each `LiveboxSensor`
  instance, so entities and separate Liveboxes do not share state. A decrease
  in router uptime resets accumulated state after a reboot.
- **Why:** Commit `ea25a04` records that module-level closures were shared
  through `SENSOR_TYPES`, corrupting counters when multiple boxes were
  configured. The README changelog also documents per-instance counters for
  multi-box setups and reboot reset behavior.
- **Where:** `sensor.py::LiveboxSensorEntityDescription`,
  `LiveboxSensor.__init__`, `LiveboxSensor._compute_rolling_32_bit`, and
  `LiveboxSensor.native_value`.
- **Protecting tests:** `tests/test_sensor.py::test_rolling_32bit_two_independent_instances_do_not_share_state`
  and `tests/test_sensor.py::test_rolling_32bit_resets_on_router_reboot`.
- **Merge pitfalls:** Do not move the state back into a module-level
  `value_fn` closure: entities from separate config entries would share it
  again. Keep the uptime-decrease reset as well as the rollover accumulation.

### 3. Preserve WAN access switch identity and manual override semantics

- **What:** WAN access switch IDs include the Livebox serial number, with
  `_migrate_wan_access_unique_ids` upgrading existing registry entries. The
  switch state follows an explicit schedule `override` even when the computed
  schedule `value` disagrees.
- **Why:** Issue #287 and commit `097e49d` document duplicate unique IDs across
  multi-box installations when the serial prefix was missing. Issue #281 and
  commit `b794fcc` document a switch incorrectly flipping back on when
  `override=Disable` conflicted with `value=Enable`.
- **Where:** `switch.py::DeviceWANAccessSwitch` and its `is_on` property;
  `__init__.py::_migrate_wan_access_unique_ids` and `async_setup_entry`.
- **Protecting tests:** `tests/test_switch.py::test_switch_wan_access`,
  `tests/test_switch.py::test_switch_wan_access_override_without_value_disable`,
  and `tests/test_switch.py::test_wan_access_switch_unique_id_migration`.
- **Merge pitfalls:** These behaviors and tests are already present in the
  upstream v2.6.0 comparison base; there is no WAN-access hunk in
  `30c75a0..origin/master`. Keep them when resolving a later upstream conflict,
  but do not blindly replay or duplicate changes already in the new base.

### 4. Use the Fibre-specific guest Wi-Fi controls

- **What:** For Livebox Fibre, turn-on uses `async_set_guest_wifi(enable=True)`
  followed by `async_set_wlan_timer`; turn-off uses
  `async_set_guest_wifi(enable=False)` followed by
  `async_disable_wlan_timer`.
- **Why:** Commit `8562e6f` says the Fibre helpers were lost in a rebase and
  restores them because the generic `async_guest_wifi` path has a timer bug.
  The README changelog records the Fibre turn-off fix.
- **Where:** `switch.py::_async_turn_on_guest_wifi_fibre`,
  `switch.py::_async_turn_off_guest_wifi_fibre`, and `SWITCH_TYPES_5`;
  `tests/conftest.py::mock_router` supplies the API mocks.
- **Protecting tests:** `tests/test_switch.py::test_switch_guest_wifi_fibre_turn_off`.
  The test exercises turn-off; it does not separately assert the Fibre turn-on
  timer call.
- **Merge pitfalls:** Do not replace these Fibre-specific actions with the
  generic `async_guest_wifi` call. In this comparison, `helpers.py` changes
  only for display-option normalization; the Fibre helpers are in `switch.py`.

### 5. Keep repeater parent links valid and compatible with HA 2025.5

- **What:** When topology assigns a client to a newly discovered repeater,
  create the repeater registry device before updating the client's
  `via_device`. If topology names a parent that is not a known repeater, keep
  the existing parent so a later refresh can retry. Look up parents with
  `async_get_device_by_identifier` when available, falling back to
  `async_get_device(identifiers=...)` for the declared minimum HA 2025.5.
- **Why:** Commit `2dce189` identifies the repeater-link behavior as fixing
  issue #191; `a0167c2` explains that HA rejects a `via_device` whose repeater
  registry entry does not yet exist. The compatibility fallback is documented
  in the 2.6.0.2 changelog and is required by the fork's HA minimum.
- **Where:** `device_tracker.py::LiveboxDeviceScannerEntity._handle_coordinator_update`
  and `LiveboxDataUpdateCoordinator.get_parent_device_identifier`.
- **Protecting tests:** `tests/test_device_tracker.py::test_device_tracker_links_clients_to_repeaters`,
  `test_device_tracker_updates_via_device_on_coordinator_refresh`,
  `test_device_tracker_creates_missing_repeater_before_via_update`,
  and `test_device_tracker_keeps_parent_when_topology_parent_is_unknown`.
- **Merge pitfalls:** Keep the missing-parent creation before the client
  registry update, and retain the legacy lookup fallback until the minimum HA
  version is raised. The tests run on the installed HA registry API; they do
  not directly exercise the fallback branch. The unknown-parent test supplies
  that condition by patching `get_parent_device_identifier`. The nearby TODO
  about removing vanished devices is deferred work, not a reason to discard
  the current parent-link behavior.

### 6. Warn on unknown ProductClass without losing Funbox6

- **What:** Map upstream `Funbox6` to model `6.1`; for any other unknown
  `ProductClass`, log a warning and set `model` to `None` rather than failing
  setup.
- **Why:** The README 2.6.0.1 changelog explicitly says to keep the upstream
  Funbox6 mapping alongside the fork's unknown-ProductClass fallback warning.
- **Where:** `coordinator.py::LiveboxDataUpdateCoordinator._async_update_data`,
  in the ProductClass match.
- **Protecting tests:** `tests/test_coordinator.py::test_unknown_product_class_logs_warning_and_sets_model_none`
  covers the fallback. No test found directly asserting the `Funbox6` → `6.1`
  mapping; add one if that mapping is changed during a sync.
- **Merge pitfalls:** Do not replace the `Funbox6` case with the fallback, or
  make unknown models fatal. Keep the warning visible for diagnosis.

### 7. Rate-limit topology builds when there are no repeaters

- **What:** Rebuild topology every 5 minutes when repeaters are known, but use
  `TOPOLOGY_SCAN_INTERVAL_NO_REPEATERS` (24 hours) with no repeaters. Set
  `_topology_cache_at` before router calls so invalid or failed builds are
  rate-limited too.
- **Why:** Owner-provided operating context: `buildTopology`
  (`topologydiagnostics.async_set_topodiags_build`) is the heaviest Livebox
  call, performs a mesh scan, and has a 30-second timeout. Upstream's 5-minute
  cadence can mean about 288 builds per day. René has no repeaters: his TP-Link
  Deco mesh is behind the Livebox on a separate sub-LAN, so the Livebox sees
  only the Deco router as an Ethernet client. The 24-hour interval reduces
  router load and the risk of stressing or crashing the Livebox.
- **Where:** `coordinator.py::TOPOLOGY_SCAN_INTERVAL`,
  `TOPOLOGY_SCAN_INTERVAL_NO_REPEATERS`,
  `LiveboxDataUpdateCoordinator._topology_scan_interval`, and
  `LiveboxDataUpdateCoordinator.async_get_topology`.
- **Protecting tests:** `tests/test_coordinator.py::test_topology_rebuilt_daily_without_repeaters`,
  `tests/test_coordinator.py::test_topology_failed_build_not_retried_every_cycle`,
  and `tests/test_coordinator.py::test_topology_rebuilt_after_scan_interval`;
  the roaming/repeater behavior is also covered by the device-tracker tests in
  entry 5.
- **Merge pitfalls:** Keep the five-minute interval for known repeaters, the
  24-hour no-repeater interval, and the timestamp assignment before any
  topology API request. Moving the timestamp to the success path reintroduces
  one-minute retries after failures.

### 8. Migrate the legacy “Active only” option

- **What:** Normalize the stored selector value `Active only` to `Active` on
  setup and in the options flow; expose only `All` and `Active` as current
  values.
- **Why:** The README 2.5.4.3 changelog records this migration, and commits
  `8e08a3f` and `436412d` describe the option mismatch and validation failure
  for older entries.
- **Where:** `const.py::DISPLAY_DEVICES_OPTIONS`;
  `helpers.py::normalize_display_devices` and `normalize_options`;
  `config_flow.py::LiveboxOptionsFlowHandler`; `coordinator.py` device filtering;
  `__init__.py::async_setup_entry`.
- **Protecting tests:** `tests/test_config_flow.py::test_options_flow_active`,
  `tests/test_config_flow.py::test_options_flow_migrates_legacy_active_only`,
  and `tests/test_setup.py::test_setup_migrates_legacy_active_only`.
- **Merge pitfalls:** Normalize before validating the options selector and
  migrate persisted options on setup; changing only the UI leaves older
  entries with an invalid stored value.

### 9. Bound the call-log calendar cache

- **What:** Prune cached calls older than 30 days in
  `LiveboxCallLogCalendar.async_get_events`, handle naive and timezone-aware
  call timestamps, and return a materialized list of events.
- **Why:** Commit `32b3d54` documents that the cache previously grew
  indefinitely until a Livebox reboot. The same diff removes a redundant unary
  plus from the call-end calculation; **Reason: not documented — ask René**
  for that adjacent cleanup.
- **Where:** `calendar.py::LiveboxCallLogCalendar.async_get_events`.
- **Protecting tests:** `tests/test_calendar.py::test_async_get_events_returns_list`
  and `tests/test_calendar.py::test_async_get_events_filters_by_range`.
  Neither test directly asserts the 30-day pruning behavior.
- **Merge pitfalls:** Preserve the rolling retention bound, aware/naive
  datetime comparison, and list return type. The current calendar tests use
  `object.__new__` and a fake coordinator, unlike the current `AGENTS.md`
  testing rules; do not copy that setup for new safeguard tests, and convert
  these tests to the AIOSysbus integration style if rewriting this file.

### 10. Other small code hunks with no documented rationale

- **What:** `async_setup_entry` resets a legacy non-string config-entry
  `unique_id` so setup can repopulate it from the router serial; the
  coordinator drops the unused `async_get_lan` argument and corrects the
  `async_detect_new_dvices` spelling; the uptime sensor icon becomes
  `mdi:progress-clock`.
- **Why:** **Reason: not documented — ask René.**
- **Where:** `__init__.py::async_setup_entry`;
  `coordinator.py::LiveboxDataUpdateCoordinator._async_update_data`,
  `async_get_lan`, and `async_detect_new_devices`;
  `sensor.py` uptime entity description.
- **Protecting tests:** `tests/test_setup.py::test_setup_entry` and
  `tests/test_setup.py::test_coordinator_refresh` provide general setup/refresh
  coverage, but no targeted test was found for these individual hunks.
- **Merge pitfalls:** Keep the `async_get_lan` call and signature aligned, and
  update both the renamed coordinator method and its caller together. Confirm
  the legacy `unique_id` migration and icon change before dropping them; their
  rationale is not recorded in the reviewed changelog or commit messages.

### 11. Fork metadata and tooling / CI

- **What:** GitHub Actions workflows run HACS and stale handling for owner
  `rjullien`; release tags accept both `X.Y.Z` and fork `X.Y.Z.N`. Dependabot
  checks GitHub Actions and `uv` weekly. `pyproject.toml` pins development
  `aiosysbus==1.2.5`, requires `pytest-homeassistant-custom-component>=0.13.346`,
  and targets Ruff at Python 3.13; `uv.lock` records those dependency and lock
  format updates. The manifest points code ownership, documentation, and issue
  tracking at the fork and carries version `2.6.0.2`. README records fork
  status, versioning, and changelog.
- **Why:** The README 2.5.4.2 changelog documents the modern development stack,
  lockfile compatibility, and four-part versioning. README 2.5.6.1 explains
  why Ruff must remain at `py313`: HA's 2025.5 runtime minimum uses Python 3.13,
  even though development/CI uses Python 3.14.
- **Where:** `.github/dependabot.yml`;
  `.github/workflows/hacs.yml`, `release.yml`, and `stale.yaml`;
  `pyproject.toml`, `uv.lock`, `custom_components/livebox/manifest.json`, and
  `README.md`.
- **Protecting tests:** No unit test covers workflow or repository metadata.
  Validate these through `uv run prek run --all-files` and the repository's
  HACS/manifest CI checks.
- **Merge pitfalls:** Do not change the fork owner back to `cyr-ius`, drop the
  four-part release glob, or raise Ruff's target to Python 3.14 while HA
  2025.5 remains supported. Regenerate `uv.lock` through `uv`, not by editing
  it manually, and keep the manifest's integration version synchronized with
  the README fork changelog.

## Upstream sync procedure

1. Keep the previous released fork state under its existing `vX.Y.Z.N` tag;
   that tag is the pre-sync checkpoint and must not be moved.
2. Rebase the fork commits onto the new upstream release tag, rather than
   merging upstream. This keeps GitHub Compare and ForkUpstreamMonitor at
   `behind_by=0`. Re-apply any safeguard that upstream did not take, resolving
   conflicts against the inventory above.
3. Set the integration version to `X.Y.Z.N`: use the new upstream
   `X.Y.Z` base and reset fork revision `N` to `.1`. Update the README **Fork
   status** and add the fork changelog entry.
4. If upstream rewrote a test file, restore the safeguard regression tests in
   the current upstream test style: drive setup through the `AIOSysbus` mock
   and real config-entry/platform setup. Do not use `object.__new__`, fake
   coordinators, or direct coordinator-method calls.
5. Install and verify from the rebased tree:

   ```bash
   uv sync
   uv run python -m pytest tests -q
   uv run prek run --all-files
   ```

   CMake must be installed for `pycares` during `uv sync`. Require the complete
   test suite to pass with coverage at or above 85%; run both pytest and prek
   before updating the branch.
6. Check the safeguard symbols and test names after the rebase. For example:

   ```bash
   rg -n 'TOPOLOGY_SCAN_INTERVAL_NO_REPEATERS|_topology_scan_interval|async_persist_session|LiveboxSessionStore|async_logout_session|_async_logout_orphaned_session|HttpRequestFailed|_compute_rolling_32_bit|_migrate_wan_access_unique_ids|_async_turn_on_guest_wifi_fibre|_async_turn_off_guest_wifi_fibre|async_get_device_by_identifier|async_get_device\\(identifiers|get_parent_device_identifier|Unknown Livebox ProductClass|Funbox6|normalize_display_devices|normalize_options|30 days' custom_components/livebox
   ```

   Also confirm the protecting test names listed above still exist and update
   this inventory if behavior or test names changed.
7. Confirm GitHub Compare/ForkUpstreamMonitor reports `behind_by=0`. Only after
   checks pass, force-push the rebased `master` (prefer
   `git push --force-with-lease origin master`).

## Deployment note

The integration runs on Home Assistant **cam** (Pi56), on the Livebox LAN;
production is behind the Deco and is not the deployment target. Deploy by
copying only changed files over SSH, file by file, then restart Home Assistant.
Do not rely on a HACS update on `cam`. Keep Livebox load low, especially during
topology-related testing.
