"""Sensor platform for IFB Washer Local integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ifb_washer_local import WasherState

from .const import DOMAIN
from .coordinator import IFBWasherCoordinator


@dataclass(frozen=True, kw_only=True)
class IFBWasherSensorEntityDescription(SensorEntityDescription):
    """Describes an IFB Washer sensor entity."""

    value_fn: Callable[[WasherState], str | int | float | None]


SENSOR_TYPES: tuple[IFBWasherSensorEntityDescription, ...] = (
    IFBWasherSensorEntityDescription(
        key="state",
        translation_key="machine_state",
        icon="mdi:washing-machine",
        value_fn=lambda state: state.state_name,
    ),
    IFBWasherSensorEntityDescription(
        key="program",
        translation_key="program",
        icon="mdi:format-list-bulleted-type",
        value_fn=lambda state: state.program_name,
    ),
    IFBWasherSensorEntityDescription(
        key="time_remaining",
        translation_key="time_remaining",
        icon="mdi:timer-outline",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda state: state.remaining_minutes,
    ),
    IFBWasherSensorEntityDescription(
        key="motor_rpm",
        translation_key="motor_rpm",
        icon="mdi:rotate-right",
        native_unit_of_measurement="RPM",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda state: state.motor_rpm,
    ),
    IFBWasherSensorEntityDescription(
        key="water_temperature",
        translation_key="water_temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda state: state.water_temperature_c,
    ),
    IFBWasherSensorEntityDescription(
        key="spin_speed_setting",
        translation_key="spin_speed_setting",
        icon="mdi:speedometer",
        value_fn=lambda state: state.spin_speed_name,
    ),
    IFBWasherSensorEntityDescription(
        key="temperature_setting",
        translation_key="temperature_setting",
        icon="mdi:thermometer-chevron-up",
        value_fn=lambda state: state.temperature_name,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up IFB Washer sensors based on a config entry."""
    coordinator: IFBWasherCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        IFBWasherSensor(coordinator, description) for description in SENSOR_TYPES
    )


class IFBWasherSensor(CoordinatorEntity[IFBWasherCoordinator], SensorEntity):
    """Representation of an IFB Washer sensor."""

    entity_description: IFBWasherSensorEntityDescription

    def __init__(
        self,
        coordinator: IFBWasherCoordinator,
        description: IFBWasherSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.client.host}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> str | int | float | None:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
