"""IFB Washer Local integration for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant

try:
    from .ifb_washer_local import DEFAULT_PORT, IFBWasherClient
except (ImportError, ValueError):
    from ifb_washer_local import DEFAULT_PORT, IFBWasherClient  # type: ignore[import-not-found, import-untyped]

from .const import DOMAIN, PLATFORMS
from .coordinator import IFBWasherCoordinator

_LOGGER = logging.getLogger(__name__)

type IFBWasherConfigEntry = ConfigEntry[IFBWasherCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: IFBWasherConfigEntry) -> bool:
    """Set up IFB Washer Local from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    host: str = entry.data[CONF_HOST]
    port: int = entry.data.get(CONF_PORT, DEFAULT_PORT)

    client = IFBWasherClient(host=host, port=port)
    # Pre-warm models lookup catalog in executor to prevent blocking I/O on event loop
    try:
        from ifb_washer_models import get_lookup

        await hass.async_add_executor_job(get_lookup)
    except Exception:
        pass

    coordinator = IFBWasherCoordinator(hass, client, entry=entry)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    hass.data[DOMAIN][entry.entry_id] = coordinator

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Migrate existing entities in entity registry to stable MAC-based unique IDs
    try:
        from homeassistant.helpers import entity_registry as er

        ent_reg = er.async_get(hass)
        existing_entries = er.async_entries_for_config_entry(ent_reg, entry.entry_id)
        target_prefix = f"{coordinator.unique_id}_"
        for entity_entry in existing_entries:
            old_uid = entity_entry.unique_id
            if old_uid and not old_uid.startswith(target_prefix):
                parts = old_uid.split("_", 1)
                if len(parts) == 2 and ("." in parts[0] or ":" in parts[0]):
                    suffix = parts[1]
                    new_uid = f"{coordinator.unique_id}_{suffix}"
                    conflict = ent_reg.async_get_entity_id(entity_entry.domain, DOMAIN, new_uid)
                    if conflict and conflict != entity_entry.entity_id:
                        _LOGGER.debug("Removing stale conflicting entity %s with unique_id %s", conflict, new_uid)
                        ent_reg.async_remove(conflict)
                    _LOGGER.info(
                        "Migrated entity %s unique_id from %s to %s",
                        entity_entry.entity_id,
                        old_uid,
                        new_uid,
                    )
                    ent_reg.async_update_entity(entity_entry.entity_id, new_unique_id=new_uid)
    except Exception as err:
        _LOGGER.debug("Entity registry migration skipped or failed: %s", err)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: IFBWasherConfigEntry) -> bool:
    """Unload an IFB Washer Local config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator = getattr(entry, "runtime_data", None) or hass.data[DOMAIN].get(entry.entry_id)
        if coordinator:
            await coordinator.client.close()
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok
