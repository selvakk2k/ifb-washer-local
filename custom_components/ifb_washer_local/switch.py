"""Switch platform for IFB Washer Local integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import IFBWasherCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up IFB Washer switches based on a config entry."""
    coordinator: IFBWasherCoordinator = getattr(entry, "runtime_data", None) or hass.data[DOMAIN][entry.entry_id]
    async_add_entities([IFBWasherChildLockSwitch(coordinator)])


class IFBWasherChildLockSwitch(
    CoordinatorEntity[IFBWasherCoordinator], SwitchEntity
):
    """Switch to toggle the washer's Child Lock feature."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: IFBWasherCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self.entity_description = SwitchEntityDescription(
            key="child_lock_switch",
            translation_key="child_lock_switch",
            icon="mdi:account-lock",
        )
        self._attr_unique_id = f"{coordinator.client.host}_child_lock_switch"
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool | None:
        """Return True if child lock is engaged."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.child_lock

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Engage child lock on the machine."""
        await self.coordinator.client.set_child_lock(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disengage child lock on the machine."""
        await self.coordinator.client.set_child_lock(False)
        await self.coordinator.async_request_refresh()
