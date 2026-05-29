"""Orange Livebox."""

import logging
import re

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import CALLID, DOMAIN, PLATFORMS
from .coordinator import LiveboxDataUpdateCoordinator

type LiveboxConfigEntry = ConfigEntry[LiveboxDataUpdateCoordinator]

CALLMISSED_SCHEMA = vol.Schema({vol.Optional(CALLID): str})
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)

# Matches the legacy format: "{mac}_wan_access" where mac contains colons/hyphens.
# e.g. "AA:BB:CC:DD:EE:FF_wan_access"
_LEGACY_WAN_ACCESS_RE = re.compile(
    r"^([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}_wan_access$"
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Livebox integration."""
    return True


def _migrate_wan_access_unique_ids(
    hass: HomeAssistant,
    entry: LiveboxConfigEntry,
    serial: str,
) -> None:
    """Migrate WAN access switch unique_ids from legacy {mac}_wan_access format.

    Prior to this fix (item 2b / issue #287), DeviceWANAccessSwitch set
    unique_id = description.key = "{mac}_wan_access" — without the serial-number
    prefix used by every other entity. This caused collisions when two Livebox
    boxes were configured.

    Migration: rename to "{serial}_{mac}_wan_access" so existing entities are
    not orphaned after the upgrade.
    """
    entity_registry = er.async_get(hass)
    migrated = 0
    for entity_entry in er.async_entries_for_config_entry(
        entity_registry, entry.entry_id
    ):
        uid = entity_entry.unique_id
        if uid and _LEGACY_WAN_ACCESS_RE.match(uid):
            new_uid = f"{serial}_{uid}"
            _LOGGER.info(
                "Migrating WAN access switch unique_id: %s → %s (issue #287)",
                uid,
                new_uid,
            )
            entity_registry.async_update_entity(
                entity_entry.entity_id, new_unique_id=new_uid
            )
            migrated += 1
    if migrated:
        _LOGGER.info(
            "Migrated %d WAN access switch unique_id(s) for entry %s",
            migrated,
            entry.entry_id,
        )


async def _async_logout_orphaned_session(
    hass: HomeAssistant, entry: LiveboxConfigEntry
) -> None:
    """Logout a session that was left open from a previous HA run.

    On HA restart, the in-memory session (cookie + contextID) is lost.
    If we persisted it before shutdown, we can still send the logout
    request to free the session slot on the Livebox.
    """
    from .session import LiveboxSessionStore, async_logout_session

    store = LiveboxSessionStore(hass, entry.entry_id)
    await store.async_load()
    if store.has_session:
        _LOGGER.info("Found orphaned Livebox session from previous run, logging out")
        from homeassistant.helpers.aiohttp_client import (
            async_get_clientsession,
        )

        session = async_get_clientsession(hass)
        success = await async_logout_session(
            session,
            store.base_url or "",
            store.cookies,
            verify_tls=store.verify_tls,
        )
        if success:
            _LOGGER.info("Orphaned session logged out successfully")
        else:
            _LOGGER.warning(
                "Failed to logout orphaned session (Livebox may be unreachable)"
            )
        await store.async_clear()


async def async_setup_entry(hass: HomeAssistant, entry: LiveboxConfigEntry) -> bool:
    """Set up Livebox as config entry."""
    # Fix: migrate unique_id from bool to string if needed (legacy entries)
    if entry.unique_id is not None and not isinstance(entry.unique_id, str):
        _LOGGER.warning(
            "Migrating Livebox config entry unique_id from %s (%s) to None",
            entry.unique_id,
            type(entry.unique_id).__name__,
        )
        hass.config_entries.async_update_entry(entry, unique_id=None)

    # Logout any orphaned session from a previous run (prevents exhaustion)
    await _async_logout_orphaned_session(hass, entry)

    coordinator = LiveboxDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    # If unique_id was cleared (migration) or missing, set it from SerialNumber
    if entry.unique_id is None and coordinator.unique_id:
        hass.config_entries.async_update_entry(entry, unique_id=coordinator.unique_id)

    # Migrate legacy WAN access switch unique_ids (issue #287)
    if coordinator.unique_id:
        _migrate_wan_access_unique_ids(hass, entry, coordinator.unique_id)

    entry.runtime_data = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def async_remove_cmissed(call) -> None:
        await coordinator.api.voiceservice.async_clear_calllist(
            {CALLID: call.data.get(CALLID)}
        )
        await coordinator.async_refresh()

    hass.services.async_register(
        DOMAIN, "remove_call_missed", async_remove_cmissed, schema=CALLMISSED_SCHEMA
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: LiveboxConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: LiveboxDataUpdateCoordinator = entry.runtime_data
    # Logout from the Livebox to free the admin session slot
    await coordinator.async_logout()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: LiveboxConfigEntry):
    """Reload device tracker if change option."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Remove config entry from a device."""
    return True
