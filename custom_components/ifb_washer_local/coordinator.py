"""DataUpdateCoordinator for IFB Washer Local integration."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from ifb_washer_local import (
    ApplianceFamily,
    FAMILY_PROGRAM_MATRICES,
    IFBConnectionError,
    IFBError,
    IFBTimeoutError,
    IFBWasherClient,
    PROGRAM_CODES_WASHER_DRYER,
    WasherState,
)

from .const import (
    CONF_CUSTOM_PROGRAMS,
    CONF_FAMILY,
    DEFAULT_FAMILY,
    DEFAULT_SCAN_INTERVAL_RUNNING,
    DEFAULT_SCAN_INTERVAL_STANDBY,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class IFBWasherCoordinator(DataUpdateCoordinator[WasherState]):
    """Coordinator to manage polling data from an IFB washing machine over LAN."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: IFBWasherClient,
        entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{client.host}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL_STANDBY),
        )
        self.client = client
        self.entry = entry
        self._current_interval = DEFAULT_SCAN_INTERVAL_STANDBY
        self._initial_cycle_duration: int = 0

        # Determine configured appliance family and program matrix
        self.appliance_family = (
            entry.data.get(CONF_FAMILY, DEFAULT_FAMILY) if entry else DEFAULT_FAMILY
        )
        custom_progs = (
            entry.data.get(CONF_CUSTOM_PROGRAMS) if entry else None
        )
        if custom_progs and isinstance(custom_progs, dict):
            self.program_map = {int(k): str(v) for k, v in custom_progs.items()}
        else:
            self.program_map = FAMILY_PROGRAM_MATRICES.get(
                self.appliance_family, PROGRAM_CODES_WASHER_DRYER
            )

        self.client.program_map = self.program_map

    @property
    def initial_cycle_duration(self) -> int:
        """Return the initial duration of the current cycle in minutes."""
        return self._initial_cycle_duration

    @property
    def cycle_progress(self) -> float | None:
        """Return the estimated completion percentage (0-100) of the current cycle."""
        if (
            not self.data
            or not self.data.is_running
            or self._initial_cycle_duration <= 0
        ):
            return None
        completed = self._initial_cycle_duration - self.data.remaining_minutes
        pct = (completed / self._initial_cycle_duration) * 100.0
        return max(0.0, min(100.0, round(pct, 1)))

    @property
    def estimated_end_time(self) -> datetime | None:
        """Return the estimated completion timestamp when actively running."""
        if (
            not self.data
            or not self.data.is_running
            or self.data.remaining_minutes <= 0
        ):
            return None
        return dt_util.utcnow() + timedelta(minutes=self.data.remaining_minutes)

    @property
    def device_info(self) -> DeviceInfo:
        """Return standardized device registry information."""
        if self.appliance_family == ApplianceFamily.WASHER_DRYER:
            model_name = "Front Load Washer Dryer (WD Executive ZXS Series)"
        elif self.appliance_family == ApplianceFamily.FRONT_LOAD:
            model_name = "Front Load (Senator / Executive Plus Series)"
        elif self.appliance_family == ApplianceFamily.TOP_LOAD_SMART:
            model_name = "Smart Top Load (SWID / SID Series)"
        else:
            model_name = "IFB Smart Washing Machine"

        return DeviceInfo(
            identifiers={(DOMAIN, self.client.host)},
            name=f"IFB Washer ({self.client.host})",
            manufacturer="IFB Industries",
            model=model_name,
            configuration_url=f"http://{self.client.host}",
        )

    async def _async_update_data(self) -> WasherState:
        """Fetch the latest state from the washing machine."""
        try:
            state = await self.client.get_state()

            # Track initial cycle duration when a cycle starts or resumes
            if state.is_running:
                if (
                    self._initial_cycle_duration <= 0
                    or state.remaining_minutes > self._initial_cycle_duration
                ):
                    self._initial_cycle_duration = state.remaining_minutes
            else:
                self._initial_cycle_duration = 0

            # Adaptive polling interval: faster updates while washing, relaxed while idle
            target_interval = (
                DEFAULT_SCAN_INTERVAL_RUNNING
                if state.is_running
                else DEFAULT_SCAN_INTERVAL_STANDBY
            )
            if target_interval != self._current_interval:
                self.update_interval = timedelta(seconds=target_interval)
                self._current_interval = target_interval

            return state
        except (IFBTimeoutError, IFBConnectionError) as err:
            raise UpdateFailed(
                f"Connection error querying IFB washer at {self.client.host}: {err}"
            ) from err
        except IFBError as err:
            raise UpdateFailed(f"Protocol error querying IFB washer: {err}") from err

