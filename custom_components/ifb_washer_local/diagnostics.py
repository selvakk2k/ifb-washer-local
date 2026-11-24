"""Diagnostics support for IFB Washer Local."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .const import CONF_MAC_ADDRESS, DOMAIN

if TYPE_CHECKING:
    from .coordinator import IFBWasherCoordinator

TO_REDACT = {
    CONF_HOST,
    CONF_MAC_ADDRESS,
    "host",
    "mac",
    "mac_address",
    "unique_id",
    "serial_number",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: IFBWasherCoordinator | None = (
        getattr(entry, "runtime_data", None)
        or hass.data.get(DOMAIN, {}).get(entry.entry_id)
    )

    coordinator_info: dict[str, Any] = {}
    if coordinator:
        raw_state: dict[str, Any] | None = None
        if coordinator.data is not None:
            if dataclasses.is_dataclass(coordinator.data):
                raw_state = dataclasses.asdict(coordinator.data)
            elif hasattr(coordinator.data, "to_dict"):
                raw_state = coordinator.data.to_dict()
            else:
                raw_state = {"repr": str(coordinator.data)}

        coordinator_info = {
            "last_update_success": coordinator.last_update_success,
            "connected": getattr(coordinator, "is_connected", None),
            "family": coordinator.appliance_family,
            "model": coordinator.model_name,
            "device_name": coordinator.device_name,
            "update_interval_seconds": (
                coordinator.update_interval.total_seconds()
                if coordinator.update_interval
                else None
            ),
            "state": raw_state,
        }

    return {
        "entry": {
            "entry_id": entry.entry_id,
            "version": entry.version,
            "domain": entry.domain,
            "title": entry.title,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": async_redact_data(dict(entry.options), TO_REDACT),
            "pref_disable_new_entities": entry.pref_disable_new_entities,
            "pref_disable_polling": entry.pref_disable_polling,
        },
        "coordinator": async_redact_data(coordinator_info, TO_REDACT),
    }
