"""Select platform for IFB Washer Local integration."""

from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

try:
    from .ifb_washer_local.const import (
        ApplianceFamily,
        DELAY_START_NAME_TO_CODE,
        DELAY_START_OPTIONS,
        DRY_NAME_TO_CODE,
        DRY_OPTIONS,
        EXTRA_RINSE_NAME_TO_CODE,
        EXTRA_RINSE_OPTIONS,
        SPIN_SPEED_OPTIONS,
        TEMPERATURE_OPTIONS,
    )
    from .ifb_washer_local.exceptions import (
        IFBConnectionError,
        IFBError,
        IFBTimeoutError,
    )
except (ImportError, ValueError):
    from ifb_washer_local.const import (  # type: ignore[import-not-found, import-untyped]
        ApplianceFamily,
        DELAY_START_NAME_TO_CODE,
        DELAY_START_OPTIONS,
        DRY_NAME_TO_CODE,
        DRY_OPTIONS,
        EXTRA_RINSE_NAME_TO_CODE,
        EXTRA_RINSE_OPTIONS,
        SPIN_SPEED_OPTIONS,
        TEMPERATURE_OPTIONS,
    )
    from ifb_washer_local.exceptions import (  # type: ignore[import-not-found, import-untyped]
        IFBConnectionError,
        IFBError,
        IFBTimeoutError,
    )

from .const import DOMAIN
from .coordinator import IFBWasherCoordinator

_LOGGER = logging.getLogger(__name__)

# Reverse mappings for easy option-to-code lookup
SPIN_NAME_TO_CODE = {name: code for code, name in SPIN_SPEED_OPTIONS.items()}
TEMP_NAME_TO_CODE = {name: code for code, name in TEMPERATURE_OPTIONS.items()}


def _get_capabilities_for_coordinator(coord: IFBWasherCoordinator):
    """Resolve active program capabilities using coordinator profile, lookup, or fallback."""
    if coord.data is None:
        return None
    return coord.get_program_capabilities(coord.data.program_code)



async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up IFB Washer select entities based on a config entry."""
    coordinator: IFBWasherCoordinator = getattr(entry, "runtime_data", None) or hass.data[DOMAIN][entry.entry_id]
    entities: list[SelectEntity] = [
        IFBWasherProgramSelect(coordinator),
        IFBWasherSpinSpeedSelect(coordinator),
        IFBWasherTemperatureSelect(coordinator),
        IFBWasherExtraRinseSelect(coordinator),
        IFBWasherDelayStartSelect(coordinator),
    ]
    if coordinator.appliance_family in (ApplianceFamily.WASHER_DRYER, "washer_dryer"):
        entities.append(IFBWasherDryModeSelect(coordinator))
    async_add_entities(entities)


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
        self._attr_unique_id = f"{coordinator.unique_id}_program_select"
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
                try:
                    updated_state = await self.coordinator.client.select_program(code)
                    self.coordinator.async_set_updated_data(updated_state)
                    await self.coordinator.async_request_refresh()
                except (IFBTimeoutError, IFBConnectionError) as err:
                    raise HomeAssistantError(f"Communication error selecting program '{option}': {err}") from err
                except IFBError as err:
                    raise HomeAssistantError(f"Washer error selecting program '{option}': {err}") from err
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
        self._attr_unique_id = f"{coordinator.unique_id}_spin_speed_select"
        self._attr_device_info = coordinator.device_info

    @property
    def options(self) -> list[str]:
        """Return the allowed spin speed options for the active program."""
        caps = _get_capabilities_for_coordinator(self.coordinator)
        base_options = list(caps.allowed_spins) if caps and caps.allowed_spins else list(SPIN_SPEED_OPTIONS.values())
        curr = self.current_option
        if curr and curr not in base_options:
            base_options.append(curr)
        return base_options

    @property
    def current_option(self) -> str | None:
        """Return the current spin speed setting."""
        if self.coordinator.data is None:
            return None
        spin_name = self.coordinator.data.spin_speed_name
        if not spin_name:
            return None
        if self.coordinator.data.rinse_hold and spin_name != "No Spin":
            combined = f"{spin_name} + Rinse Hold"
            caps = _get_capabilities_for_coordinator(self.coordinator)
            if caps and caps.allowed_spins and combined in caps.allowed_spins:
                return combined
        return spin_name

    async def async_select_option(self, option: str) -> None:
        """Change the spin speed."""
        is_rinse_hold = option.endswith(" + Rinse Hold")
        base_option = option.replace(" + Rinse Hold", "") if is_rinse_hold else option

        spin_code = SPIN_NAME_TO_CODE.get(base_option)
        if spin_code is None:
            _LOGGER.warning("Unknown spin speed option selected: %s", option)
            return

        current_prog = self.coordinator.data.program_code if self.coordinator.data else None
        current_temp = self.coordinator.data.temperature_code if self.coordinator.data else None

        try:
            # If selecting a pure spin speed and Rinse Hold was on, disable Rinse Hold first
            if not is_rinse_hold and self.coordinator.data and self.coordinator.data.rinse_hold:
                try:
                    await self.coordinator.client.set_rinse_hold(False)
                except Exception:
                    pass

            updated_state = await self.coordinator.client.set_spin_speed(
                spin_code,
                program_code=current_prog,
                temp_code=current_temp,
            )

            # If selecting linked Rinse Hold option, ensure Rinse Hold bit is set
            if is_rinse_hold and not updated_state.rinse_hold:
                try:
                    updated_state = await self.coordinator.client.set_rinse_hold(True)
                except Exception:
                    pass

            self.coordinator.async_set_updated_data(updated_state)
            await self.coordinator.async_request_refresh()
        except (IFBTimeoutError, IFBConnectionError) as err:
            raise HomeAssistantError(f"Communication error setting spin speed '{option}': {err}") from err
        except IFBError as err:
            raise HomeAssistantError(f"Washer error setting spin speed '{option}': {err}") from err


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
        self._attr_unique_id = f"{coordinator.unique_id}_temperature_select"
        self._attr_device_info = coordinator.device_info

    @property
    def options(self) -> list[str]:
        """Return the allowed temperature options for the active program."""
        caps = _get_capabilities_for_coordinator(self.coordinator)
        base_options = list(caps.allowed_temps) if caps and caps.allowed_temps else list(TEMPERATURE_OPTIONS.values())
        curr = self.current_option
        if curr and curr not in base_options:
            base_options.append(curr)
        return base_options

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

        current_prog = self.coordinator.data.program_code if self.coordinator.data else None
        current_spin = self.coordinator.data.spin_speed_code if self.coordinator.data else None

        try:
            updated_state = await self.coordinator.client.set_temperature(
                temp_code,
                program_code=current_prog,
                spin_code=current_spin,
            )
            self.coordinator.async_set_updated_data(updated_state)
            await self.coordinator.async_request_refresh()
        except (IFBTimeoutError, IFBConnectionError) as err:
            raise HomeAssistantError(f"Communication error setting temperature '{option}': {err}") from err
        except IFBError as err:
            raise HomeAssistantError(f"Washer error setting temperature '{option}': {err}") from err


class IFBWasherDelayStartSelect(CoordinatorEntity[IFBWasherCoordinator], SelectEntity):
    """Selector entity for choosing Delay Start duration."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: IFBWasherCoordinator) -> None:
        """Initialize the delay start selector."""
        super().__init__(coordinator)
        self.entity_description = SelectEntityDescription(
            key="delay_start_select",
            translation_key="delay_start_select",
            icon="mdi:timer-outline",
        )
        self._attr_unique_id = f"{coordinator.unique_id}_delay_start_select"
        self._attr_device_info = coordinator.device_info
        self._attr_options = list(DELAY_START_OPTIONS.values())

    @property
    def current_option(self) -> str | None:
        """Return the current delay start setting."""
        if self.coordinator.data is None:
            return None
        total_mins = getattr(self.coordinator.data, "delay_start_minutes", 0)
        if total_mins <= 0:
            return "No Delay"
        if total_mins <= 30:
            return "30 Minutes"
        hours = round(total_mins / 60)
        return DELAY_START_OPTIONS.get(hours * 2, f"{hours} Hours")

    async def async_select_option(self, option: str) -> None:
        """Change the delay start duration."""
        code = DELAY_START_NAME_TO_CODE.get(option)
        if code is None:
            _LOGGER.warning("Unknown delay start option selected: %s", option)
            return

        try:
            updated_state = await self.coordinator.client.set_delay_start(code)
            self.coordinator.async_set_updated_data(updated_state)
            await self.coordinator.async_request_refresh()
        except (IFBTimeoutError, IFBConnectionError) as err:
            raise HomeAssistantError(f"Communication error setting delay start '{option}': {err}") from err
        except IFBError as err:
            raise HomeAssistantError(f"Washer error setting delay start '{option}': {err}") from err


class IFBWasherExtraRinseSelect(CoordinatorEntity[IFBWasherCoordinator], SelectEntity):
    """Selector entity for configuring Extra Rinse cycles (0 to 3)."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: IFBWasherCoordinator) -> None:
        """Initialize the extra rinse selector."""
        super().__init__(coordinator)
        self.entity_description = SelectEntityDescription(
            key="extra_rinse_select",
            translation_key="extra_rinse_select",
            icon="mdi:water-plus",
        )
        self._attr_unique_id = f"{coordinator.unique_id}_extra_rinse_select"
        self._attr_device_info = coordinator.device_info

    @property
    def options(self) -> list[str]:
        """Return the allowed extra rinse options for the active program."""
        caps = _get_capabilities_for_coordinator(self.coordinator)
        if caps and not getattr(caps, "supports_extra_rinse", True):
            return ["0 (None)"]
        max_rinses = getattr(caps, "max_extra_rinses", 3)
        if max_rinses == 2:
            return ["0 (None)", "+1 Rinse", "+2 Rinses"]
        elif max_rinses == 1:
            return ["0 (None)", "+1 Rinse"]
        elif max_rinses == 0:
            return ["0 (None)"]
        return list(EXTRA_RINSE_OPTIONS.values())

    @property
    def current_option(self) -> str | None:
        """Return the current extra rinse setting."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.extra_rinse_name

    async def async_select_option(self, option: str) -> None:
        """Change the extra rinse setting."""
        code = EXTRA_RINSE_NAME_TO_CODE.get(option)
        if code is None:
            _LOGGER.warning("Unknown extra rinse option selected: %s", option)
            return

        try:
            updated_state = await self.coordinator.client.set_extra_rinse(code)
            self.coordinator.async_set_updated_data(updated_state)
            await self.coordinator.async_request_refresh()
        except (IFBTimeoutError, IFBConnectionError) as err:
            raise HomeAssistantError(f"Communication error setting extra rinse '{option}': {err}") from err
        except IFBError as err:
            raise HomeAssistantError(f"Washer error setting extra rinse '{option}': {err}") from err


class IFBWasherDryModeSelect(CoordinatorEntity[IFBWasherCoordinator], SelectEntity):
    """Selector entity for choosing Washer Dryer drying mode."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: IFBWasherCoordinator) -> None:
        """Initialize the dry mode selector."""
        super().__init__(coordinator)
        self.entity_description = SelectEntityDescription(
            key="dry_mode_select",
            translation_key="dry_mode_select",
            icon="mdi:tumble-dryer",
        )
        self._attr_unique_id = f"{coordinator.unique_id}_dry_mode_select"
        self._attr_device_info = coordinator.device_info
        self._attr_options = list(DRY_OPTIONS.values())

    @property
    def options(self) -> list[str]:
        """Return the available drying mode options for current program."""
        caps = _get_capabilities_for_coordinator(self.coordinator)
        base_options = list(caps.allowed_dry_modes) if caps and caps.allowed_dry_modes else list(DRY_OPTIONS.values())
        curr = self.current_option
        if curr and curr not in base_options:
            base_options.append(curr)
        return base_options


    @property
    def current_option(self) -> str | None:
        """Return the current drying mode."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.dry_mode_name

    async def async_select_option(self, option: str) -> None:
        """Change the drying mode."""
        code = DRY_NAME_TO_CODE.get(option)
        if code is None:
            _LOGGER.warning("Unknown dry mode selected: %s", option)
            return

        try:
            updated_state = await self.coordinator.client.set_dry_mode(code)
            self.coordinator.async_set_updated_data(updated_state)
            await self.coordinator.async_request_refresh()
        except (IFBTimeoutError, IFBConnectionError) as err:
            raise HomeAssistantError(f"Communication error setting dry mode '{option}': {err}") from err
        except IFBError as err:
            raise HomeAssistantError(f"Washer error setting dry mode '{option}': {err}") from err

