"""DataUpdateCoordinator for IFB Washer Local integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from ifb_washer_local import (
    IFBConnectionError,
    IFBError,
    IFBTimeoutError,
    IFBWasherClient,
    WasherState,
)

from .const import (
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
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{client.host}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL_STANDBY),
        )
        self.client = client
        self._current_interval = DEFAULT_SCAN_INTERVAL_STANDBY

    @property
    def device_info(self) -> DeviceInfo:
        """Return standardized device registry information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.client.host)},
            name=f"IFB Washer ({self.client.host})",
            manufacturer="IFB Industries",
            model="Front Load Washer Dryer (742 Series)",
            configuration_url=f"http://{self.client.host}",
        )

    async def _async_update_data(self) -> WasherState:
        """Fetch the latest state from the washing machine."""
        try:
            state = await self.client.get_state()

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
            raise UpdateFailed(f"Connection error querying IFB washer at {self.client.host}: {err}") from err
        except IFBError as err:
            raise UpdateFailed(f"Protocol error querying IFB washer: {err}") from err
