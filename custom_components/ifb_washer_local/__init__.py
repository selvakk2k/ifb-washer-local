"""IFB Washer Local integration for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ifb_washer_local import DEFAULT_PORT, IFBWasherClient

from .const import DOMAIN, PLATFORMS
from .coordinator import IFBWasherCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up IFB Washer Local from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    host: str = entry.data[CONF_HOST]
    port: int = entry.data.get(CONF_PORT, DEFAULT_PORT)

    session = async_get_clientsession(hass)
    client = IFBWasherClient(host=host, port=port, session=session)
    coordinator = IFBWasherCoordinator(hass, client)

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an IFB Washer Local config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: IFBWasherCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.client.close()

    return unload_ok
