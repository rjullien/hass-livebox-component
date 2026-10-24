# Fork safeguards for upstream syncs

This inventory was checked against `git diff 2.6.1-beta4...HEAD`, where
`2.6.1-beta4` (`0e7fb0a`) is the upstream base and `HEAD` is fork release
`2.6.1.1`. The entries below account for the fork's remaining code, test,
workflow, and tooling differences. Reasons are grounded in the fork changelog,
linked issues, or owner-provided operating context; anything not documented is
marked explicitly rather than inferred.

See the README's [Upstream contributions](README.md#upstream-contributions) section for current proposals and status.

## Safeguard inventory

### 1. Persist, release, and recover Livebox sessions

- **What:** Persist each entry's session cookies, context ID, base URL, and TLS
  verification setting after successful polling, but write only when that
  tuple changes. Use upstream `aiosysbus 1.2.6` logout on unload, HA stop,
  failed first refresh, and config flow. Before setup, attempt to release a
  persisted orphan left by a crash or power loss. On a top-level
  `HttpRequestFailed`, clear the in-memory session token so the next polling
  cycle can authenticate again.
- **Logout mechanism:** Upstream `self.api.async_logout()` handles normal
  logout. Orphan cleanup posts to the stored `/ws` URL with session cookies,
  `Authorization: X-Sah-Logout <context_id>`, content type
  `application/x-sah-ws-1-call+json`, and a `releaseContext` request for
  `sah.Device.Information` with application name `so_sdkut`. Success requires
  HTTP 200 and JSON `{"status": 0}`.
- **Verification:** Confirmed on a Livebox Fibre running firmware
  `ARFI-fr-G06.R06.C01_12` on 2026-10-10. The web UI's logout request releases
  the context; a subsequent call using it returns error 13. Using a normal
  `X-Context` header returns error 196618.
- **Why:** The Livebox has a limited session table. Orphaned sessions otherwise
  remain until timeout; repeated HA restarts/reloads can exhaust the table and
  make the API stop responding. This is documented by commit `f37b631` (issue
  #8) and the README fork changelog. Commit `fb7a9bc` documents why a stale
  token must be invalidated after a communication failure.
- **Where:** `session.py::LiveboxSessionStore` and
  `session.py::async_logout_session`; `coordinator.py::async_persist_session`,
  `coordinator.py::async_logout`, and
  `LiveboxDataUpdateCoordinator._async_update_data`;
  `__init__.py::_async_logout_orphaned_session` and `async_setup_entry`.
- **Protecting tests:** `tests/test_session.py::test_logout_session_success`,
  `test_logout_session_failure_payload`, `test_logout_session_failure_status`,
  `test_logout_session_exception`, `test_logout_session_non_json`,
  `test_logout_session_missing_context_id`,
  `test_store_save_load_roundtrip`, `test_store_clear`,
  `test_coordinator_persists_only_changed_session`,
  `test_unload_calls_api_logout_and_clears_persisted_session`, and
  `test_orphan_cleanup_on_boot`.
- **Merge pitfalls:** Do not revert to `/logout.cmd`; it returned HTTP 404 on
  Livebox Fibre. Preserve the `X-Sah-Logout` header and `releaseContext` body,
  and pass the stored context ID with the cookies and TLS setting for orphan
  logout. Keep storage scoped to the config entry. Stop platform polling
  before logging out on unload. Keep token invalidation in the top-level
  update failure path; the `f37b631` commit explains that clearing it for every
  endpoint failure can trigger a login storm during one polling cycle. The
  current tests do not directly assert token invalidation after
  `HttpRequestFailed`; the persistence optimization is exercised by
  `test_coordinator_persists_only_changed_session`. Preserve both paths when
  changing coordinator error handling.

  **Operational note:** On René's real Livebox, startup can log
  `Failed to logout orphaned session (Livebox may be unreachable)`. This
  best-effort logout warning is harmless when data starts flowing immediately
  afterward; do not mistake the warning alone for a failed integration setup.

### 2. Rolling 32-bit counters (aligned with upstream in 2.6.1.1)

- **Status:** Upstream now keeps rollover state per entity. The fork-specific
  implementation and multi-box regression test were removed.
- **Where:** `sensor.py::get_rolling_32_bit_value_fn` and `SENSOR_TYPES` use
  upstream behavior.
- **Protecting tests:** No fork-only counter tests remain.
- **Merge pitfalls:** Keep the upstream per-entity rollover handling; do not
  restore older module-level shared state.

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

### 4. Fibre guest Wi-Fi helpers (removed in 2.6.0.3)

- **Status:** The fork-only helpers were removed in 2.6.0.3; keep upstream's
  `async_guest_wifi` callbacks in `SWITCH_TYPES_5`.
- **Why:** With pinned aiosysbus 1.2.6, `NMC.async_guest_wifi` makes the same
  calls: `set_guest_wifi` plus `set_wlan_timer(0, "guest")` on enable, and
  `disable_wlan_timer("guest")` on disable. The helpers only worked around an
  older aiosysbus and are no longer needed.
- **Where:** `switch.py::SWITCH_TYPES_5`.
- **Protecting tests:** None; the fork-only
  `test_switch_guest_wifi_fibre_turn_off` test was removed in 2.6.0.3.
- **Merge pitfalls:** Do not re-add the Fibre helpers; retain the upstream
  callbacks, which include the timer operations in the pinned aiosysbus.

### 5. Repeater parent links (aligned with upstream in 2.6.1.1)

- **Status:** Upstream now provides `via_device_id`, resolves parent registry
  entries with `async_get_device_by_identifier`, and updates existing links
  through `entity._async_update_via_device`. The legacy lookup fallback and
  fork-only unknown-parent behavior were removed.
- **Why:** The upstream implementation uses current Home Assistant registry
  APIs; the fork minimum is now HA 2026.8.0.
- **Where:** `entity.py`, `device_tracker.py`, `switch.py`, and
  `LiveboxDataUpdateCoordinator.get_parent_device_id`.
- **Protecting tests:** Upstream registry tests including
  `tests/test_device_tracker.py::test_device_tracker_links_clients_to_repeaters`
  and the compatible fork test
  `test_device_tracker_updates_via_device_on_coordinator_refresh`.
- **Merge pitfalls:** Keep upstream `via_device_id` and
  `_async_update_via_device`; do not restore the
  `async_get_device(identifiers=...)` compatibility fallback.

### 6. Unknown ProductClass fallback (removed in 2.6.0.3)

- **Status:** The unknown-ProductClass warning and fallback were removed in
  2.6.0.3; retain upstream's `Funbox6` → `6.1` mapping.
- **Known issue:** An unknown `ProductClass` leaves `model` unset silently.
  This is accepted to stay aligned with upstream; see README's "Known issues
  (accepted)" section.
- **Where:** `coordinator.py::LiveboxDataUpdateCoordinator._async_update_data`;
  the `Funbox6` case remains upstream behavior.
- **Protecting tests:** None; the fork-only
  `test_unknown_product_class_logs_warning_and_sets_model_none` test was
  removed in 2.6.0.3.
- **Merge pitfalls:** Keep the upstream match without a catch-all warning or
  fallback; do not remove the `Funbox6` case.

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

### 8. Display-device option (aligned with upstream in 2.6.1.1)

- **Status:** Upstream uses `DEFAULT_DISPLAY_DEVICES = "Active only"` and maps
  stored values in the options form. Any value other than `"All"` is treated
  as active, so existing `"Active"` settings remain valid without migration.
- **Where:** `const.py`, `config_flow.py`, and coordinator device filtering.
- **Protecting tests:** `tests/test_config_flow.py::test_options_flow_active`
  and `test_options_flow_defaults_are_valid`.
- **Merge pitfalls:** Keep the upstream options mapping and do not restore
  `DISPLAY_DEVICES_OPTIONS`, normalization helpers, or setup-time migration.

### 9. Call-log calendar

- **Status:** Upstream now fixes overlapping call windows. The fork's 30-day
  pruning remains removed; upstream still does not prune the cache.
- **Why:** Cache growth is accepted: it is cleared when the Livebox reboots,
  uses only a few hundred bytes per call, and the owner's line receives
  practically no calls.
- **Where:** `calendar.py::LiveboxCallLogCalendar`.
- **Protecting tests:** `tests/test_calendar.py::test_calendar_returns_overlapping_calls`.
- **Merge pitfalls:** Keep the upstream overlapping-window fix and do not
  re-introduce pruning.

### 10. Preserve the legacy `unique_id` guard

- **What:** `async_setup_entry` resets a legacy non-string config-entry
  `unique_id` so setup can repopulate it from the router serial; the reset is a
  no-op when `unique_id` is already a string. The uptime icon is now aligned
  with upstream as `mdi:progress-clock`.
- **Why:** The origin of the legacy non-string `unique_id` reset is
  undocumented; it is a no-op when `unique_id` is already a string. The
  upstream uptime icon fix was merged as cyr-ius#353.
- **Where:** `__init__.py::async_setup_entry` and `sensor.py`.
- **Protecting tests:** `tests/test_setup.py::test_setup_entry` and
  `tests/test_setup.py::test_coordinator_refresh` provide general
  setup/refresh coverage.
- **Merge pitfalls:** Keep the non-string guard and leave the uptime icon
  aligned with upstream.

### 11. Fork metadata and tooling / CI

- **What:** GitHub Actions workflows run HACS and stale handling for owner
  `rjullien`; release tags accept both `X.Y.Z` and fork `X.Y.Z.N`. Dependabot
  checks GitHub Actions and `uv` weekly. `pyproject.toml` pins development
  `aiosysbus==1.2.6`, requires `pytest-homeassistant-custom-component>=0.13.346`,
  and targets Ruff at Python 3.14; `uv.lock` records those dependency and lock
  format updates. The manifest points code ownership, documentation, and issue
  tracking at the fork and carries version `2.6.1.1`. HACS declares minimum HA
  2026.8.0; README records fork status, versioning, and changelog.
- **Why:** The README changelog documents the modern development stack,
  lockfile compatibility, and four-part versioning. Upstream now requires HA
  2026.8.0 and uses Python 3.14 syntax.
- **Where:** `.github/dependabot.yml`;
  `.github/workflows/hacs.yml`, `release.yml`, and `stale.yaml`;
  `pyproject.toml`, `uv.lock`, `custom_components/livebox/manifest.json`, and
  `README.md`.
- **Protecting tests:** No unit test covers workflow or repository metadata.
  Validate these through `uv run prek run --all-files` and the repository's
  HACS/manifest CI checks.
- **Merge pitfalls:** Do not change the fork owner back to `cyr-ius` or drop
  the four-part release glob. Regenerate `uv.lock` through `uv`, not by editing
  it manually, and keep the manifest's integration version synchronized with
  the README fork changelog.

### 12. Retain device state when the device-list read fails

- **What:** When `Devices.async_get_devices` raises `AiosysbusException`,
  `async_get_devices` returns the prior device list and counters from
  coordinator data, or empty defaults before the first successful read, for at
  most three consecutive failures. The fourth failure raises `UpdateFailed`,
  making every integration entity unavailable through `CoordinatorEntity`.
  Consumers must treat an unavailable tracker as unknown, not away. Any
  successful read resets the counter. A successful empty response remains a
  valid empty device list.
- **Why:** `_make_request` converts endpoint exceptions to `{}`, which otherwise
  makes a transient device-list failure look like a successful empty response
  and marks tracked devices away.
- **Where:** `coordinator.py::LiveboxDataUpdateCoordinator.async_get_devices`.
- **Protecting tests:** `tests/test_device_tracker.py::test_device_tracker_retains_last_state_when_device_read_fails`,
  `test_device_list_read_failure_limit_resets_after_success`,
  `test_initial_device_read_failure_uses_empty_defaults`, and
  `test_legitimately_empty_device_list_clears_previous_data`.
- **Merge pitfalls:** Keep this exception handling scoped to the device-list
  read; do not change `_make_request` behavior for other endpoints. Do not
  retain old state for a successful empty response.

## Upstream sync procedure

1. Keep the previous released fork state under its existing `vX.Y.Z.N` tag;
   that tag is the pre-sync checkpoint and must not be moved.
2. Merge the upstream release tag into a fork sync branch with
   `git merge --no-ff <tag>`. If upstream changes were ported manually, record
   ancestry afterward with `git merge -s ours <tag>`. Never squash, rebase,
   or force-push. Re-apply only safeguards that upstream did not take,
   resolving conflicts against the inventory above and avoiding cosmetic-only
   divergence.
3. Set the integration version to `X.Y.Z.N`: use the new upstream
   `X.Y.Z` base and reset fork revision `N` to `.1`. Update the README **Fork
   status** and add the fork changelog entry.
4. If upstream rewrote a test file, keep only relevant safeguard regression
   tests in the current upstream test style: drive setup through the
   `AIOSysbus` mock and real config-entry/platform setup. Do not use
   `object.__new__`, fake coordinators, or direct coordinator-method calls.
5. Install and verify from the merged tree:

   ```bash
   uv sync
   uv run python -m pytest tests -q
   uv run prek run --all-files
   ```

   CMake must be installed for `pycares` during `uv sync`. Require the complete
   test suite to pass with coverage at or above 85%; run both pytest and prek
   before pushing the branch.

6. Check the safeguard symbols and test names after the merge. For example:

   ```bash
   rg -n 'TOPOLOGY_SCAN_INTERVAL_NO_REPEATERS|_topology_scan_interval|async_persist_session|LiveboxSessionStore|async_logout_session|_async_logout_orphaned_session|HttpRequestFailed|_migrate_wan_access_unique_ids|async_get_device_by_identifier|get_parent_device_id|Funbox6' custom_components/livebox
   ```

   Also confirm the protecting test names listed above still exist and update
   this inventory if behavior or test names changed.

7. Finish when `git rev-list --left-right --count <tag>...origin/master`
   prints `0 <ahead>` after the ancestry-preserving sync reaches
   `origin/master`. Push sync branches normally; never force-push.

## Deployment note

The integration runs on Home Assistant **cam** (Pi56), on the Livebox LAN;
production is behind the Deco and is not the deployment target. Deploy by
copying only changed files over SSH, file by file, then restart Home Assistant.
Do not rely on a HACS update on `cam`. Keep Livebox load low, especially during
topology-related testing.
