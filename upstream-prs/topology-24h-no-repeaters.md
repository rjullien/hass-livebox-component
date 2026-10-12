Title: perf(coordinator): rebuild topology once a day when there is no repeater

## Problem

`async_get_topology` calls `Devices`/`topologyDiagnostics.buildTopology`, one
of the heaviest requests the Livebox serves, and the coordinator refreshes it
every 5 minutes so `via_device` links follow client roaming between mesh
repeaters.

When the site has **no repeater**, clients physically cannot roam: every
device's parent is the Livebox itself. The 5-minute rebuild then buys nothing
— it only adds a heavy sysbus call every cycle on routers that are already the
weakest link (and on firmwares where `buildTopology` is expensive).

## Proposal

Keep the current 5-minute interval **when at least one repeater exists**
(`topology_repeaters` non-empty — roaming is possible). When there is no
repeater, stretch the rebuild to **24 hours**. The cached result is still
returned between rebuilds; the first scan at setup is unchanged, so new
repeaters are picked up within a day at worst.

This is behaviour-preserving for everyone with a mesh, and purely reduces
router load for everyone without one.

## Tested on a real router

Livebox Fibre (Arcadyan), firmware `ARFI-fr-G06.R06.C01_12`, no repeater on the
LAN: the integration issues `buildTopology` once a day instead of ~288 times,
with identical `via_device` results.

## Tests (AIOSysbus mock, per AGENTS.md)

No repeaters in the topology response → the cached topology is still served
past the 5-minute mark and rebuilt after 24 h; a repeater present → the
5-minute interval still applies.

Running in `rjullien/hass-livebox-component` since 2.6.0.x.
