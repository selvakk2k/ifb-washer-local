"""Select platform for IFB Washer Local integration."""

from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ifb_washer_local.const import (
    SPIN_SPEED_OPTIONS,
    TEMPERATURE_OPTIONS,
)

from .const import DOMAIN
from .coordinator import IFBWasherCoordinator

_LOGGER = logging.getLogger(__name__)

# Reverse mappings for easy option-to-code lookup
SPIN_NAME_TO_CODE = {name: code for code, name in SPIN_SPEED_OPTIONS.items()}
TEMP_NAME_TO_CODE = {name: code for code, name in TEMPERATURE_OPTIONS.items()}



async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up IFB Washer select entities based on a config entry."""
    coordinator: IFBWasherCoordinator = getattr(entry, "runtime_data", None) or hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            IFBWasherProgramSelect(coordinator),
            IFBWasherSpinSpeedSelect(coordinator),
            IFBWasherTemperatureSelect(coordinator),
        ]
    )


class IFBWasherProgramSelect(CoordinatorEntity[IFBWasherCoordinator], SelectEntity):
    """Selector entity for choosing wash programs."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: IFBWasherCoordinator) -> None:
        """Initialize the program selector."""
        super().__init__(coordinator)
        self.entity_description = SelectEntityDescription(
            key="program_select",
            translation_key="program_select",
            icon="mdi:format-list-checks",
        )
        self._attr_unique_id = f"{coordinator.client.host}_program_select"
        self._attr_device_info = coordinator.device_info

    @property
    def options(self) -> list[str]:
        """Return the available program options for this appliance family."""
        return list(self.coordinator.program_map.values())

    @property
    def current_option(self) -> str | None:
        """Return the currently selected program."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.program_name

    async def async_select_option(self, option: str) -> None:
        """Change the selected wash program."""
        for code, name in self.coordinator.program_map.items():
            if name == option:
                await self.coordinator.client.select_program(code)
                await self.coordinator.async_request_refresh()
                return
        _LOGGER.warning("Unknown program option selected: %s", option)



class IFBWasherSpinSpeedSelect(CoordinatorEntity[IFBWasherCoordinator], SelectEntity):
    """Selector entity for choosing spin speeds."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: IFBWasherCoordinator) -> None:
        """Initialize the spin speed selector."""
        super().__init__(coordinator)
        self.entity_description = SelectEntityDescription(
            key="spin_speed_select",
            translation_key="spin_speed_select",
            icon="mdi:speedometer",
        )
        self._attr_unique_id = f"{coordinator.client.host}_spin_speed_select"
        self._attr_device_info = coordinator.device_info
        self._attr_options = list(SPIN_SPEED_OPTIONS.values())

    @property
    def current_option(self) -> str | None:
        """Return the current spin speed setting."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.spin_speed_name

    async def async_select_option(self, option: str) -> None:
        """Change the spin speed."""
        spin_code = SPIN_NAME_TO_CODE.get(option)
        if spin_code is None:
            _LOGGER.warning("Unknown spin speed option selected: %s", option)
            return

        await self.coordinator.client.set_spin_speed(spin_code)
        await self.coordinator.async_request_refresh()


class IFBWasherTemperatureSelect(CoordinatorEntity[IFBWasherCoordinator], SelectEntity):
    """Selector entity for choosing wash temperatures."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: IFBWasherCoordinator) -> None:
        """Initialize the temperature selector."""
        super().__init__(coordinator)
        self.entity_description = SelectEntityDescription(
            key="temperature_select",
            translation_key="temperature_select",
            icon="mdi:thermometer-chevron-up",
        )
        self._attr_unique_id = f"{coordinator.client.host}_temperature_select"
        self._attr_device_info = coordinator.device_info
        self._attr_options = [
            name for code, name in TEMPERATURE_OPTIONS.items() if code != 0
        ]

    @property
    def current_option(self) -> str | None:
        """Return the current temperature setting."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.temperature_name

    async def async_select_option(self, option: str) -> None:
        """Change the temperature."""
        temp_code = TEMP_NAME_TO_CODE.get(option)
        if temp_code is None:
            _LOGGER.warning("Unknown temperature option selected: %s", option)
            return

        await self.coordinator.client.set_temperature(temp_code)
        await self.coordinator.async_request_refresh()
