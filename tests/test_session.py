"""Tests for Livebox session management (logout + persistence)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientSession

from custom_components.livebox.session import (
    LiveboxSessionStore,
    async_logout_session,
)

# ---------------------------------------------------------------------------
# G1 — Unit: async_logout_session
# ---------------------------------------------------------------------------


class _FakeResponse:
    """Minimal async context manager mimicking aiohttp response."""

    def __init__(self, status: int) -> None:
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


@pytest.mark.parametrize("status", [200, 301, 302, 307])
async def test_logout_session_success_statuses(status: int) -> None:
    """Logout returns True for success-like HTTP status codes."""
    mock_session = MagicMock(spec=ClientSession)
    mock_session.get = MagicMock(return_value=_FakeResponse(status))

    result = await async_logout_session(
        mock_session,
        "http://192.168.1.1/ws",
        {"sessid": "abc123"},
        verify_tls=True,
    )
    assert result is True

    # Verify the URL called
    call_args = mock_session.get.call_args
    url = call_args[0][0]
    assert url.endswith("/logout.cmd")

    # Verify Cookie header
    headers = call_args[1]["headers"]
    assert "sessid=abc123" in headers["Cookie"]

    # Verify ssl parameter
    assert call_args[1]["ssl"] is True


async def test_logout_session_verify_tls_false() -> None:
    """When verify_tls=False, ssl=False is passed to disable cert check."""
    mock_session = MagicMock(spec=ClientSession)
    mock_session.get = MagicMock(return_value=_FakeResponse(307))

    result = await async_logout_session(
        mock_session,
        "https://192.168.1.1/ws",
        {"SESSIONID": "xyz789"},
        verify_tls=False,
    )
    assert result is True

    call_args = mock_session.get.call_args
    assert call_args[1]["ssl"] is False


async def test_logout_session_failure_status() -> None:
    """Logout returns False for non-success status codes."""
    mock_session = MagicMock(spec=ClientSession)
    mock_session.get = MagicMock(return_value=_FakeResponse(404))

    result = await async_logout_session(
        mock_session,
        "http://192.168.1.1/ws",
        {"sessid": "abc123"},
    )
    assert result is False


async def test_logout_session_exception() -> None:
    """Logout returns False when an exception occurs."""
    mock_session = MagicMock(spec=ClientSession)
    mock_session.get = MagicMock(side_effect=OSError("Connection refused"))

    result = await async_logout_session(
        mock_session,
        "http://192.168.1.1/ws",
        {"sessid": "abc123"},
    )
    assert result is False


async def test_logout_session_multiple_cookies() -> None:
    """Multiple cookies are joined with semicolons."""
    mock_session = MagicMock(spec=ClientSession)
    mock_session.get = MagicMock(return_value=_FakeResponse(307))

    await async_logout_session(
        mock_session,
        "http://192.168.1.1/ws",
        {"sessid": "aaa", "token": "bbb"},
    )

    call_args = mock_session.get.call_args
    cookie_header = call_args[1]["headers"]["Cookie"]
    assert "sessid=aaa" in cookie_header
    assert "token=bbb" in cookie_header


# ---------------------------------------------------------------------------
# G2 — Unit: LiveboxSessionStore round-trip
# ---------------------------------------------------------------------------


async def test_store_save_load_roundtrip(hass) -> None:
    """Save → load round-trip preserves all fields."""
    store = LiveboxSessionStore(hass, "test_entry_123")

    await store.async_save(
        cookies={"sessid": "cookie_val"},
        context_id="ctx_abc",
        base_url="http://192.168.1.1/ws",
        verify_tls=False,
    )

    # Create a fresh store instance (simulates restart)
    store2 = LiveboxSessionStore(hass, "test_entry_123")
    await store2.async_load()

    assert store2.has_session is True
    assert store2.cookies == {"sessid": "cookie_val"}
    assert store2.context_id == "ctx_abc"
    assert store2.base_url == "http://192.168.1.1/ws"
    assert store2.verify_tls is False


async def test_store_clear(hass) -> None:
    """async_clear empties the store."""
    store = LiveboxSessionStore(hass, "test_entry_clear")
    await store.async_save(
        cookies={"sessid": "x"},
        context_id="ctx",
        base_url="http://x/ws",
    )
    assert store.has_session is True

    await store.async_clear()
    assert store.has_session is False
    assert store.cookies == {}
    assert store.context_id is None


async def test_store_verify_tls_default(hass) -> None:
    """verify_tls defaults to True when not persisted (legacy data)."""
    store = LiveboxSessionStore(hass, "test_entry_legacy")
    # Simulate loading legacy data without verify_tls field
    store._data = {
        "cookies": {"sessid": "old"},
        "context_id": "old_ctx",
        "base_url": "http://192.168.1.1/ws",
    }
    assert store.verify_tls is True


# ---------------------------------------------------------------------------
# G3 — Integration: unload calls logout
# ---------------------------------------------------------------------------


async def test_unload_calls_logout(hass) -> None:
    """async_unload_entry triggers coordinator.async_logout."""
    from custom_components.livebox import async_unload_entry

    mock_coordinator = MagicMock()
    mock_coordinator.async_logout = AsyncMock()

    mock_entry = MagicMock()
    mock_entry.runtime_data = mock_coordinator

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        return_value=True,
    ):
        result = await async_unload_entry(hass, mock_entry)

    assert result is True
    mock_coordinator.async_logout.assert_awaited_once()


async def test_unload_no_runtime_data(hass) -> None:
    """async_unload_entry handles missing runtime_data gracefully."""
    from custom_components.livebox import async_unload_entry

    mock_entry = MagicMock(spec=[])  # No runtime_data attribute

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        return_value=True,
    ):
        result = await async_unload_entry(hass, mock_entry)

    assert result is True


# ---------------------------------------------------------------------------
# G4 — Integration: orphan cleanup on boot
# ---------------------------------------------------------------------------


async def test_orphan_cleanup_on_boot(hass) -> None:
    """Pre-populated store triggers logout and is cleared on setup."""
    from custom_components.livebox import _async_logout_orphaned_session

    mock_entry = MagicMock()
    mock_entry.entry_id = "test_orphan_entry"

    # Pre-populate the store
    store = LiveboxSessionStore(hass, "test_orphan_entry")
    await store.async_save(
        cookies={"sessid": "orphan_cookie"},
        context_id="orphan_ctx",
        base_url="http://192.168.1.1/ws",
        verify_tls=True,
    )

    with patch(
        "custom_components.livebox.session.async_logout_session",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_logout:
        await _async_logout_orphaned_session(hass, mock_entry)

    # Verify logout was called with correct cookies, url and verify_tls
    mock_logout.assert_awaited_once()
    call_kwargs = mock_logout.call_args
    # positional: (session, base_url, cookies)
    assert call_kwargs[0][1] == "http://192.168.1.1/ws"
    assert call_kwargs[0][2] == {"sessid": "orphan_cookie"}
    assert call_kwargs[1]["verify_tls"] is True

    # Verify store was cleared
    store2 = LiveboxSessionStore(hass, "test_orphan_entry")
    await store2.async_load()
    assert store2.has_session is False
