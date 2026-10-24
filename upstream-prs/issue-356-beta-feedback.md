Beta feedback for https://github.com/cyr-ius/hass-livebox-component/issues/356
(post as one comment, in English)

---

Thanks for the beta — running `2.6.1-beta4` (aiosysbus 1.2.6) for two weeks
(since 2026-10-11), now together with current `master` (incl. #360) on a Livebox Fibre (Arcadyan, firmware
`ARFI-fr-G06.R06.C01_12`), Home Assistant 2026.9.3.

So far everything looks good on my side:

- session logout on unload/stop works — the context is really released;
- `via_device_id` repeater linking, the "Active only" option and the uptime
  icon all behave as expected;
- no new warning or error in the logs since the upgrade.

One gap remains vs. the idea in my closed PR #352 — and it is the only part I
still carry in my fork: **the logout only happens on a clean stop**. If HA
crashes or the machine loses power, the session stays open on the router
until it times out, and the Livebox session table is small — a few unclean
restarts can exhaust it. This is not theoretical for me: the HA box is a
Raspberry Pi 3 at a remote site, and its kernel log shows short undervoltage
events about once a day, plus one unclean power loss on 2026-10-23 — none of
those reach `async_unload`.

The fix I run: persist the session (`context_id`, cookies, `base_url`,
`verify_tls`) to `.storage` whenever it changes, and at setup release any
leftover session with the same `X-Sah-Logout` + `releaseContext` request
before opening a new one. On clean unload the store is cleared after
`api.async_logout()`. Verified on the real router: the released context is
rejected with error 13 afterwards.

If you think that belongs upstream I can open a PR — otherwise I'll keep it
in the fork, it is harmless alongside your logout.
