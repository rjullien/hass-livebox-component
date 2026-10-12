Title: fix(session): survive crashes and re-authenticate after transport failures

## Problem

`2.6.1-beta` (PR #354 + aiosysbus 1.2.6) releases the Livebox session on a clean
unload, HA stop and config-flow abort — thank you for that. Two gaps remain:

1. **A crash or power loss never reaches `async_unload`.** The context stays
   open on the router until it expires. The Livebox session table is small, so
   a few unclean restarts (or a stormy night at a rural site) can exhaust it
   and the API stops accepting logins until sessions time out.
2. **After a transport failure the stale token is reused.** When a poll dies
   with `HttpRequestFailed` (connection reset, empty reply), the next cycle
   retries with the same session token. If the router already dropped it, the
   entry keeps erroring instead of logging in again.

Both are rare per-day but deterministic over months, exactly the failures a
remote, unattended install cannot recover from alone.

## Proposal

- **Persist the session** (`context_id`, cookies, `base_url`, `verify_tls`)
  to `.storage/livebox_session.<entry_id>`, written only when the tuple
  changes — not on every poll.
- **Release orphans at setup:** before opening a new session, POST the stored
  credentials with the same `X-Sah-Logout` + `releaseContext` request the web
  UI uses for logout (the mechanism #354 already relies on). Success is only
  HTTP 200 with `status == 0`; anything else logs at debug level and never
  blocks setup.
- **Clear the store on clean unload**, after `api.async_logout()` runs — a
  clean stop does not leave a stale context to be released at the next boot.
- **Re-authenticate after transport failure:** on a top-level
  `HttpRequestFailed`, clear `session_token` so the next poll logs in again.
  Deliberately scoped to the _top-level_ failure path only: clearing the token
  on every individual endpoint error caused a login storm inside a single
  polling cycle (seen on the fork, commit `fb7a9bc`).

## Tested on a real router

Livebox Fibre (Arcadyan), firmware `ARFI-fr-G06.R06.C01_12`:

- `releaseContext` answers `{"status": 0}` with the persisted cookies and
  `X-Sah-Logout <context_id>`;
- a call made afterwards with the released context returns error 13
  "Permission denied" — the context is really gone;
- after a simulated crash (HA killed), the next boot releases the leftover
  session before logging in.

## Tests (AIOSysbus mock, per AGENTS.md)

Orphan release attempted at setup and store cleared afterwards; store
save/load/clear roundtrip; persistence writes only when credentials change;
clean unload clears the store; `HttpRequestFailed` clears the token so the
next refresh re-authenticates.

This is what `rjullien/hass-livebox-component` has been running in production
for months; happy to adapt the patch to whatever shape you prefer in aiosysbus
or the component.
