# AGENTS.md

## Cursor Cloud specific instructions

This repo is a **single Home Assistant custom integration** (`custom_components/livebox/`,
domain `livebox`) for Orange Livebox routers. It is not a standalone app or a monorepo — the
"application" runs inside Home Assistant Core. Dependencies are managed with `uv` (Python
3.14, see `pyproject.toml`; deps live in the `dev` dependency group).

### Standard dev commands

These are already documented in `README.md` (Development section). Assume the update script has
already run `uv sync --group dev`, so the `.venv` is ready.

- Tests: `uv run pytest`
- Lint/format/all hooks: `uv run prek run --all-files`

The automated test suite is fully self-contained: `pytest-homeassistant-custom-component` boots a
mock Home Assistant in-process and the Livebox router is mocked via `aiosysbus` + JSON fixtures in
`tests/fixtures/`. **No real router, database, or external service is required to run tests.**

### Non-obvious gotchas

- **Ruff is not a direct dependency.** `uv run ruff ...` will fail with "Failed to spawn: ruff".
  Run lint via `uv run prek run --all-files` (prek manages the ruff hook environment). The first
  `prek` run downloads hook environments (needs network).
- **`uv sync` resets the venv to the lockfile.** It removes any packages installed ad-hoc with
  `uv pip install`. Don't rely on manually-installed extras surviving a sync.

### Running a live Home Assistant server (optional, manual testing only)

Not needed for tests. Only do this to manually exercise the integration's UI/config flow:

1. Create a config dir with the component linked, e.g.
   `mkdir -p /tmp/ha_config/custom_components && ln -sfn /workspace/custom_components/livebox /tmp/ha_config/custom_components/livebox`,
   and a minimal `configuration.yaml` containing `frontend:`, `config:`, `api:` (avoid
   `default_config:` — it pulls in heavy optional integrations that fail without extra native libs).
2. Run `uv run hass -c /tmp/ha_config` (serves on `http://localhost:8123`).
3. Home Assistant auto-installs some optional deps at first boot. Two of them (`pymicro-vad`,
   `pyspeex-noise`, pulled in by `assist_pipeline`) are C++ and **fail to build with the default
   `/usr/bin/c++` (clang), which cannot find libstdc++ headers**. If the dashboard hangs on
   "Loading data", install them forcing gcc:
   `CC=gcc CXX=g++ uv pip install pymicro-vad==1.0.1 pyspeex-noise==1.0.2`, then restart `hass`.
   These extras are removed again by any later `uv sync` (see gotcha above) — that's fine, they are
   not part of the dev/test workflow.
4. Completing the integration's config flow past the connection step requires a real Orange Livebox
   router on the network, which is not available in the cloud VM. The config flow renders and runs
   its connection logic, then reports a connection error without a router — this is expected.
