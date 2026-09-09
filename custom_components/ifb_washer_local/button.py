"""Button platform for IFB Washer Local integration."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ifb_washer_local import IFBWasherClient

from .const import DOMAIN
from .coordinator import IFBWasherCoordinator


@dataclass(frozen=True, kw_only=True)
class IFBWasherButtonEntityDescription(ButtonEntityDescription):
    """Describes an IFB Washer button entity."""

    press_action: Callable[[IFBWasherClient], Awaitable[None]]


BUTTON_TYPES: tuple[IFBWasherButtonEntityDescription, ...] = (
    IFBWasherButtonEntityDescription(
        key="start",
        translation_key="start",
        icon="mdi:play",
        press_action=lambda client: client.start(),
    ),
    IFBWasherButtonEntityDescription(
        key="pause",
        translation_key="pause",
        icon="mdi:pause",
        press_action=lambda client: client.pause(),
    ),
    IFBWasherButtonEntityDescription(
        key="cancel",
        translation_key="cancel",
        icon="mdi:stop",
        press_action=lambda client: client.cancel(),
    ),
    IFBWasherButtonEntityDescription(
        key="power_off",
        translation_key="power_off",
        icon="mdi:power",
        press_action=lambda client: client.power_off(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up IFB Washer buttons based on a config entry."""
    coordinator: IFBWasherCoordinator = getattr(entry, "runtime_data", None) or hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        IFBWasherButton(coordinator, description) for description in BUTTON_TYPES
    )


class IFBWasherButton(CoordinatorEntity[IFBWasherCoordinator], ButtonEntity):
    """Representation of an IFB Washer action button."""

    _attr_has_entity_name = True
    entity_description: IFBWasherButtonEntityDescription

    def __init__(
        self,
        coordinator: IFBWasherCoordinator,
        description: IFBWasherButtonEntityDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.client.host}_{description.key}"
        self._attr_device_info = coordinator.device_info

    async def async_press(self) -> None:
        """Handle the button press action."""
        await self.entity_description.press_action(self.coordinator.client)
        await self.coordinator.async_request_refresh()
