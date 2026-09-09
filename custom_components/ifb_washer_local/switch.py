"""Switch platform for IFB Washer Local integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

try:
    from .ifb_washer_local.const import (
        HIL_OPTION_ANTI_CREASE,
        HIL_OPTION_AROMA,
        HIL_OPTION_ECO,
        HIL_OPTION_HOT_RINSE,
        HIL_OPTION_PRE_WASH,
        HIL_OPTION_RINSE_HOLD,
        HIL_OPTION_SOAK,
        HIL_OPTION_STEAM,
        HIL_OPTION_TIME_SAVER,
    )
    from .ifb_washer_local.exceptions import (
        IFBConnectionError,
        IFBError,
        IFBTimeoutError,
    )
except (ImportError, ValueError):
    from ifb_washer_local.const import (  # type: ignore[import-not-found, import-untyped]
        HIL_OPTION_ANTI_CREASE,
        HIL_OPTION_AROMA,
        HIL_OPTION_ECO,
        HIL_OPTION_HOT_RINSE,
        HIL_OPTION_PRE_WASH,
        HIL_OPTION_RINSE_HOLD,
        HIL_OPTION_SOAK,
        HIL_OPTION_STEAM,
        HIL_OPTION_TIME_SAVER,
    )
    from ifb_washer_local.exceptions import (  # type: ignore[import-not-found, import-untyped]
        IFBConnectionError,
        IFBError,
        IFBTimeoutError,
    )

from .const import DOMAIN
from .coordinator import IFBWasherCoordinator

FEATURE_SWITCHES: tuple[tuple[str, str, str, int, str], ...] = (
    ("prewash", "prewash", "mdi:washing-machine-alert", HIL_OPTION_PRE_WASH, "prewash"),
    ("soak", "soak", "mdi:water-opacity", HIL_OPTION_SOAK, "soak"),
    ("rinse_hold", "rinse_hold", "mdi:water-pause", HIL_OPTION_RINSE_HOLD, "rinse_hold"),
    ("time_saver", "time_saver", "mdi:clock-fast", HIL_OPTION_TIME_SAVER, "time_saver"),
    ("hot_rinse", "hot_rinse", "mdi:water-thermometer", HIL_OPTION_HOT_RINSE, "hot_rinse"),
    ("eco", "eco", "mdi:leaf", HIL_OPTION_ECO, "eco"),
    ("steam", "steam", "mdi:weather-fog", HIL_OPTION_STEAM, "steam"),
    ("aroma", "aroma", "mdi:flower-tulip-outline", HIL_OPTION_AROMA, "aroma"),
    ("anti_crease", "anti_crease", "mdi:iron", HIL_OPTION_ANTI_CREASE, "anti_crease"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up IFB Washer switches based on a config entry."""
    coordinator: IFBWasherCoordinator = getattr(entry, "runtime_data", None) or hass.data[DOMAIN][entry.entry_id]
    entities: list[SwitchEntity] = [
        IFBWasherPowerSwitch(coordinator),
        IFBWasherChildLockSwitch(coordinator),
    ]
    for key, translation_key, icon, hil_id, state_attr in FEATURE_SWITCHES:
        entities.append(
            IFBWasherFeatureSwitch(
                coordinator,
                key=key,
                translation_key=translation_key,
                icon=icon,
                hil_id=hil_id,
                state_attr=state_attr,
            )
        )
    async_add_entities(entities)


class IFBWasherPowerSwitch(
    CoordinatorEntity[IFBWasherCoordinator], SwitchEntity
):
    """Switch to toggle the washer's power state (On / Standby)."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: IFBWasherCoordinator) -> None:
        """Initialize the power switch."""
        super().__init__(coordinator)
        self.entity_description = SwitchEntityDescription(
            key="power",
            translation_key="power",
            icon="mdi:power",
            device_class=SwitchDeviceClass.SWITCH,
        )
        self._attr_unique_id = f"{coordinator.client.host}_power_switch"
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool | None:
        """Return True if the machine is powered on."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.is_powered_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Power on the machine."""
        try:
            state = await self.coordinator.client.power_on()
            self.coordinator.async_set_updated_data(state)
            await self.coordinator.async_request_refresh()
        except (IFBTimeoutError, IFBConnectionError) as err:
            raise HomeAssistantError(f"Communication error powering on washer: {err}") from err
        except IFBError as err:
            raise HomeAssistantError(f"Washer error powering on: {err}") from err

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Power off the machine into low-power standby."""
        try:
            state = await self.coordinator.client.power_off()
            self.coordinator.async_set_updated_data(state)
            await self.coordinator.async_request_refresh()
        except (IFBTimeoutError, IFBConnectionError) as err:
            raise HomeAssistantError(f"Communication error powering off washer: {err}") from err
        except IFBError as err:
            raise HomeAssistantError(f"Washer error powering off: {err}") from err


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
        try:
            await self.coordinator.client.set_child_lock(True)
            await self.coordinator.async_request_refresh()
        except (IFBTimeoutError, IFBConnectionError) as err:
            raise HomeAssistantError(f"Communication error enabling child lock: {err}") from err
        except IFBError as err:
            raise HomeAssistantError(f"Washer error enabling child lock: {err}") from err

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disengage child lock on the machine."""
        try:
            await self.coordinator.client.set_child_lock(False)
            await self.coordinator.async_request_refresh()
        except (IFBTimeoutError, IFBConnectionError) as err:
            raise HomeAssistantError(f"Communication error disabling child lock: {err}") from err
        except IFBError as err:
            raise HomeAssistantError(f"Washer error disabling child lock: {err}") from err


class IFBWasherFeatureSwitch(
    CoordinatorEntity[IFBWasherCoordinator], SwitchEntity
):
    """Switch to toggle individual wash cycle modifier features."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: IFBWasherCoordinator,
        key: str,
        translation_key: str,
        icon: str,
        hil_id: int,
        state_attr: str,
    ) -> None:
        """Initialize the feature modifier switch."""
        super().__init__(coordinator)
        self.hil_id = hil_id
        self.state_attr = state_attr
        self.entity_description = SwitchEntityDescription(
            key=key,
            translation_key=translation_key,
            icon=icon,
        )
        self._attr_unique_id = f"{coordinator.client.host}_{key}_switch"
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool | None:
        """Return True if the feature is currently enabled."""
        if self.coordinator.data is None:
            return None
        return getattr(self.coordinator.data, self.state_attr, False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the feature."""
        try:
            state = await self.coordinator.client.set_feature_toggle(self.hil_id, True)
            self.coordinator.async_set_updated_data(state)
            await self.coordinator.async_request_refresh()
        except (IFBTimeoutError, IFBConnectionError) as err:
            raise HomeAssistantError(f"Communication error enabling {self.entity_description.key}: {err}") from err
        except IFBError as err:
            raise HomeAssistantError(f"Washer error enabling {self.entity_description.key}: {err}") from err

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the feature."""
        try:
            state = await self.coordinator.client.set_feature_toggle(self.hil_id, False)
            self.coordinator.async_set_updated_data(state)
            await self.coordinator.async_request_refresh()
        except (IFBTimeoutError, IFBConnectionError) as err:
            raise HomeAssistantError(f"Communication error disabling {self.entity_description.key}: {err}") from err
        except IFBError as err:
            raise HomeAssistantError(f"Washer error disabling {self.entity_description.key}: {err}") from err

