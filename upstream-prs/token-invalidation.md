Title: fix(coordinator): re-authenticate after a transport failure

## Problem

When a polling cycle fails at the top level with `HttpRequestFailed`
(connection reset, empty reply, router-side 5xx), the coordinator comes back
on the next cycle with the **same** session token. If the Livebox has dropped
the session in the meantime — its session table is small and entries get
evicted — every following call keeps failing on auth until something else
resets the token. On a remote, unattended install the entry can stay broken
for days while the router itself is healthy.

## Proposal

On a top-level `HttpRequestFailed`, clear `session_token` so the next polling
cycle re-authenticates:

```python
if isinstance(error, HttpRequestFailed):
    self.api._auth.session_token = None
```

Deliberately scoped to the **top-level** failure path only: clearing the
token on every individual endpoint error triggered a login storm inside a
single polling cycle in our fork (commit `fb7a9bc`). The fix costs nothing on
the normal path — the re-authentication simply replaces a call that would
have failed anyway.

## Tested on a real router

Livebox Fibre (Arcadyan), firmware `ARFI-fr-G06.R06.C01_12`: after a dropped
session the integration recovered on the next 30-second poll instead of
looping on auth errors.

## Tests (AIOSysbus mock, per AGENTS.md)

A top-level `HttpRequestFailed` clears the token and the following refresh
re-authenticates and succeeds; non-transport errors leave the token alone.

Running in `rjullien/hass-livebox-component` since 2.6.0.x.
