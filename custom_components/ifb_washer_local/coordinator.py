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

try:
    from .ifb_washer_local import (
        ApplianceFamily,
        FAMILY_PROGRAM_MATRICES,
        IFBConnectionError,
        IFBError,
        IFBTimeoutError,
        IFBWasherClient,
        PROGRAM_CODES_WASHER_DRYER,
        ProgramCapabilities,
        WasherState,
        calibrate_appliance_detailed,
        calibrate_appliance_quick,
        calibrate_appliance_simple,
        deserialize_capabilities_map,
        serialize_capabilities_map,
    )
    from .ifb_washer_local.const import (
        PROGRAM_CAPABILITIES_FRONT_LOAD,
        PROGRAM_CAPABILITIES_TOP_LOAD,
        PROGRAM_CAPABILITIES_WASHER_DRYER,
        get_program_capabilities as get_default_capabilities,
    )
except (ImportError, ValueError):
    from ifb_washer_local import (  # type: ignore[import-not-found, import-untyped]
        ApplianceFamily,
        FAMILY_PROGRAM_MATRICES,
        IFBConnectionError,
        IFBError,
        IFBTimeoutError,
        IFBWasherClient,
        PROGRAM_CODES_WASHER_DRYER,
        ProgramCapabilities,
        WasherState,
        calibrate_appliance_detailed,
        calibrate_appliance_quick,
        calibrate_appliance_simple,
        deserialize_capabilities_map,
        serialize_capabilities_map,
    )
    from ifb_washer_local.const import (  # type: ignore[import-not-found, import-untyped]
        PROGRAM_CAPABILITIES_FRONT_LOAD,
        PROGRAM_CAPABILITIES_TOP_LOAD,
        PROGRAM_CAPABILITIES_WASHER_DRYER,
        get_program_capabilities as get_default_capabilities,
    )

from .const import (
    CONF_CALIBRATED_PROFILE,
    CONF_CUSTOM_MODEL,
    CONF_CUSTOM_PROGRAMS,
    CONF_FAMILY,
    CONF_MODEL,
    CONF_SCAN_INTERVAL_RUNNING,
    CONF_SCAN_INTERVAL_STANDBY,
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
        standby_interval = DEFAULT_SCAN_INTERVAL_STANDBY
        if entry and isinstance(getattr(entry, "options", None), dict):
            standby_interval = entry.options.get(
                CONF_SCAN_INTERVAL_STANDBY, DEFAULT_SCAN_INTERVAL_STANDBY
            )

        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{client.host}",
            update_interval=timedelta(seconds=standby_interval),
        )
        self.client = client
        self.entry = entry
        self._current_interval = standby_interval
        self._initial_cycle_duration: int = 0
        self._is_calibrating: bool = False

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

        # Load persisted calibration profile if available
        self.calibrated_caps: dict[int, ProgramCapabilities] = {}
        if entry:
            options_dict = entry.options if isinstance(getattr(entry, "options", None), dict) else {}
            data_dict = entry.data if isinstance(getattr(entry, "data", None), dict) else {}
            cal_data = options_dict.get(CONF_CALIBRATED_PROFILE) or data_dict.get(CONF_CALIBRATED_PROFILE)
            if cal_data and isinstance(cal_data, dict):
                self.calibrated_caps = deserialize_capabilities_map(cal_data)
                _LOGGER.info(
                    "Loaded custom calibrated profile for IFB Washer (%d programs calibrated)",
                    len(self.calibrated_caps),
                )


    @property
    def initial_cycle_duration(self) -> int:
        """Return the initial duration of the current cycle in minutes."""
        return self._initial_cycle_duration

    @property
    def cycle_progress(self) -> float | None:
        """Return the estimated completion percentage (0-100) of the current cycle."""
        if not self.data:
            return None
        prog = getattr(self.data, "cycle_progress", 0.0)
        if isinstance(prog, (int, float)) and prog > 0.0:
            return float(prog)
        if getattr(self.data, "is_complete", False):
            return 100.0
        if not self.data.is_running or self._initial_cycle_duration <= 0:
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
    def model_name(self) -> str:
        """Return the user-selected or auto-resolved model name."""
        if self.entry:
            options = self.entry.options if isinstance(getattr(self.entry, "options", None), dict) else {}
            data = self.entry.data if isinstance(getattr(self.entry, "data", None), dict) else {}
            custom_m = options.get(CONF_CUSTOM_MODEL) or data.get(CONF_CUSTOM_MODEL)
            if custom_m:
                return str(custom_m)
            m = options.get(CONF_MODEL) or data.get(CONF_MODEL)
            if m and m != "custom":
                return str(m)

        if self.appliance_family == ApplianceFamily.WASHER_DRYER:
            return "Washer Dryer (WD Executive ZXS Series)"
        if self.appliance_family == ApplianceFamily.FRONT_LOAD:
            return "Front Load (Senator / Executive Plus Series)"
        if self.appliance_family == ApplianceFamily.TOP_LOAD_SMART:
            return "Top Load (Smart Top Load Series)"
        return "IFB Smart Washing Machine"

    @property
    def device_info(self) -> DeviceInfo:
        """Return standardized device registry information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.client.host)},
            name=f"IFB {self.model_name} ({self.client.host})",
            manufacturer="IFB Industries",
            model=self.model_name,
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
            standby_interval = DEFAULT_SCAN_INTERVAL_STANDBY
            running_interval = DEFAULT_SCAN_INTERVAL_RUNNING
            if self.entry and isinstance(getattr(self.entry, "options", None), dict):
                standby_interval = self.entry.options.get(
                    CONF_SCAN_INTERVAL_STANDBY, DEFAULT_SCAN_INTERVAL_STANDBY
                )
                running_interval = self.entry.options.get(
                    CONF_SCAN_INTERVAL_RUNNING, DEFAULT_SCAN_INTERVAL_RUNNING
                )

            target_interval = (
                running_interval if state.is_running else standby_interval
            )
            if target_interval != self._current_interval:
                self.update_interval = timedelta(seconds=target_interval)
                self._current_interval = target_interval

            _LOGGER.debug(
                "Coordinator poll (%s): state='%s'(%d), is_running=%s, door_locked=%s, prog='%s'(%d), rem=%dm",
                self.client.host,
                state.state_name,
                state.state_code,
                state.is_running,
                state.door_locked,
                state.program_name,
                state.program_code,
                state.remaining_minutes,
            )

            return state
        except (IFBTimeoutError, IFBConnectionError) as err:
            raise UpdateFailed(
                f"Connection error querying IFB washer at {self.client.host}: {err}"
            ) from err
        except IFBError as err:
            raise UpdateFailed(f"Protocol error querying IFB washer: {err}") from err

    def get_program_capabilities(
        self, program_code: int | None = None
    ) -> ProgramCapabilities | None:
        """Resolve capabilities for a program code using calibrated profile or catalog defaults."""
        if program_code is None:
            if self.data is None:
                return None
            program_code = self.data.program_code

        # 1. First priority: Exact calibrated capabilities from physical machine probing
        if program_code in self.calibrated_caps:
            return self.calibrated_caps[program_code]

        # 2. Second priority: ifb_washer_models catalog lookup
        try:
            try:
                from ifb_washer_models import get_lookup
            except ImportError:
                from .ifb_washer_models import get_lookup
            lookup = get_lookup()
            manual_code = getattr(self, "manual_code", "MAN_742_E")
            prog_name = self.program_map.get(program_code, str(program_code))
            caps = lookup.get_program_capabilities(manual_code, prog_name)
            if caps:
                return caps
        except Exception:
            pass

        # 3. Third priority: Static family tables or generic fallback
        if self.appliance_family == ApplianceFamily.FRONT_LOAD:
            return PROGRAM_CAPABILITIES_FRONT_LOAD.get(
                program_code, get_default_capabilities(program_code)
            )
        if self.appliance_family == ApplianceFamily.TOP_LOAD_SMART:
            return PROGRAM_CAPABILITIES_TOP_LOAD.get(
                program_code, get_default_capabilities(program_code)
            )
        return PROGRAM_CAPABILITIES_WASHER_DRYER.get(
            program_code, get_default_capabilities(program_code)
        )

    async def async_calibrate(
        self, mode: str = "quick"
    ) -> dict[int, ProgramCapabilities]:
        """Run online hardware capability calibration against the physical appliance."""
        if self._is_calibrating:
            _LOGGER.warning("Calibration is already in progress for %s", self.client.host)
            return self.calibrated_caps

        # Check if appliance is busy
        if self.data and (self.data.is_running or self.data.is_paused):
            raise UpdateFailed("Cannot run calibration while a wash cycle is active")

        self._is_calibrating = True
        _LOGGER.info(
            "Starting %s hardware capability calibration for IFB washer at %s",
            mode,
            self.client.host,
        )
        is_wd = self.appliance_family in (ApplianceFamily.WASHER_DRYER, "washer_dryer")

        if self.appliance_family == ApplianceFamily.FRONT_LOAD:
            base_map = PROGRAM_CAPABILITIES_FRONT_LOAD
        elif self.appliance_family == ApplianceFamily.TOP_LOAD_SMART:
            base_map = PROGRAM_CAPABILITIES_TOP_LOAD
        else:
            base_map = PROGRAM_CAPABILITIES_WASHER_DRYER

        try:
            if mode == "detailed":
                new_caps = await calibrate_appliance_detailed(
                    self.client,
                    self.program_map,
                    base_map,
                    is_washer_dryer=is_wd,
                )
            elif mode == "simple":
                new_caps = await calibrate_appliance_simple(
                    self.client,
                    self.program_map,
                    base_map,
                    is_washer_dryer=is_wd,
                )
            else:
                new_caps = await calibrate_appliance_quick(
                    self.client,
                    self.program_map,
                    base_map,
                    is_washer_dryer=is_wd,
                )
            self.calibrated_caps = new_caps

            # Persist to config entry data
            if self.entry:
                serialized = serialize_capabilities_map(new_caps)
                new_data = dict(self.entry.data)
                new_data[CONF_CALIBRATED_PROFILE] = serialized
                self.hass.config_entries.async_update_entry(self.entry, data=new_data)

            _LOGGER.info(
                "Hardware calibration completed successfully for %s (%d programs mapped)",
                self.client.host,
                len(new_caps),
            )
            await self.async_request_refresh()
            return new_caps
        finally:
            self._is_calibrating = False


