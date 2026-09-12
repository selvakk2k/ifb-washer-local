"""Binary sensor platform for IFB Washer Local integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

try:
    from .ifb_washer_local import WasherState
except (ImportError, ValueError):
    from ifb_washer_local import WasherState  # type: ignore[import-not-found, import-untyped]

from .const import DOMAIN
from .coordinator import IFBWasherCoordinator


@dataclass(frozen=True, kw_only=True)
class IFBWasherBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes an IFB Washer binary sensor entity."""

    is_on_fn: Callable[[WasherState], bool]


BINARY_SENSOR_TYPES: tuple[IFBWasherBinarySensorEntityDescription, ...] = (
    IFBWasherBinarySensorEntityDescription(
        key="running",
        translation_key="running",
        device_class=BinarySensorDeviceClass.RUNNING,
        is_on_fn=lambda state: state.is_running,
    ),
    IFBWasherBinarySensorEntityDescription(
        key="door_locked",
        translation_key="door_locked",
        device_class=BinarySensorDeviceClass.LOCK,
        # DeviceClass.LOCK: False means locked (secure), True means unlocked
        is_on_fn=lambda state: not state.door_locked,
    ),
    IFBWasherBinarySensorEntityDescription(
        key="child_lock",
        translation_key="child_lock",
        icon="mdi:account-lock",
        is_on_fn=lambda state: state.child_lock,
    ),
    IFBWasherBinarySensorEntityDescription(
        key="problem",
        translation_key="problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
        is_on_fn=lambda state: state.has_problem,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up IFB Washer binary sensors based on a config entry."""
    coordinator: IFBWasherCoordinator = getattr(entry, "runtime_data", None) or hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        IFBWasherBinarySensor(coordinator, description)
        for description in BINARY_SENSOR_TYPES
    )


class IFBWasherBinarySensor(
    CoordinatorEntity[IFBWasherCoordinator], BinarySensorEntity
):
    """Representation of an IFB Washer binary sensor."""

    _attr_has_entity_name = True
    entity_description: IFBWasherBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: IFBWasherCoordinator,
        description: IFBWasherBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.unique_id}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.is_on_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra diagnostic attributes for sensors."""
        if self.entity_description.key == "problem" and self.coordinator.data is not None:
            return {
                "error_code": self.coordinator.data.error_code,
                "error_description": self.coordinator.data.error_description,
            }
        return None

