Title: fix(session): release the Livebox session on unload and on restart

## Problem

The integration never logs out. Each time HA restarts or the integration is reloaded, its Livebox session (context) is left open until it expires on the router. The Livebox only accepts a limited number of sessions, so several restarts in a short time can leave the API refusing new logins.

## Fix

- **Release the session on unload** with the same request the Livebox web UI makes when you log out (`common/commonLoader.js` → `logOut`):
  ```
  POST http://<host>/ws
  Authorization: X-Sah-Logout <contextID>      # instead of X-Context
  Cookie: <session cookies>
  {"service": "sah.Device.Information", "method": "releaseContext",
   "parameters": {"applicationName": "so_sdkut"}}
  -> 200 {"status": 0}
  ```
  Calling `releaseContext` with the usual `X-Context` header returns error 196618 "Object or parameter not found". The `X-Sah-Logout` authorization header is what releases the context.
- **Clean up after a crash or power loss:** the session credentials (context ID, cookies, base URL, `verify_tls`) are persisted in `.storage/livebox_session.<entry_id>`. At setup, a session left over from the previous run is released before a new one is opened. The credentials are written only when they change, not on every poll.
- **Success criterion:** the logout counts as successful only on HTTP 200 with `status == 0`. Any failure is logged at debug level and never blocks setup or unload.

## Tested on a real router

On a Livebox Fibre (Arcadyan, firmware ARFI-fr-G06.R06.C01_12):

- `releaseContext` returns `{"status": 0}`;
- an authenticated call made afterwards with the old context gets error 13 "Permission denied";
- after an HA restart, the context persisted by the previous run is released the same way.

## Tests

Unit tests for the request (URL, headers, body, `ssl`), its failure cases (non-200, `errors` payload, exception, missing context ID), the orphan cleanup at setup, the logout at unload, and persistence that writes only when the credentials change.
