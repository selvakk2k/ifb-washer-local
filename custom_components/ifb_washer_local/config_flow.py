"""Config flow for IFB Washer Local integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.dhcp import DhcpServiceInfo
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

import json

try:
    from .ifb_washer_local import (
        DEFAULT_PORT,
        ApplianceFamily,
        FAMILY_PROGRAM_MATRICES,
        IFBConnectionError,
        IFBError,
        IFBTimeoutError,
        IFBWasherClient,
        PROGRAM_CODES_FRONT_LOAD,
        PROGRAM_CODES_TOP_LOAD,
        PROGRAM_CODES_WASHER_DRYER,
        WasherState,
        calibrate_appliance_detailed,
        calibrate_appliance_quick,
        calibrate_appliance_simple,
        deserialize_capabilities_map,
        extract_profile_metadata,
        save_profile_backup,
        serialize_capabilities_map,
    )
    from .ifb_washer_local.const import (
        DIAL_SIDES_BY_FAMILY,
        MACHINE_TYPE_LABELS,
        MODELS_BY_FAMILY,
        PROGRAM_CAPABILITIES_FRONT_LOAD,
        PROGRAM_CAPABILITIES_TOP_LOAD,
        PROGRAM_CAPABILITIES_WASHER_DRYER,
    )
except (ImportError, ValueError):
    from ifb_washer_local import (  # type: ignore[import-not-found, import-untyped]
        DEFAULT_PORT,
        ApplianceFamily,
        FAMILY_PROGRAM_MATRICES,
        IFBConnectionError,
        IFBError,
        IFBTimeoutError,
        IFBWasherClient,
        PROGRAM_CODES_FRONT_LOAD,
        PROGRAM_CODES_TOP_LOAD,
        PROGRAM_CODES_WASHER_DRYER,
        WasherState,
        calibrate_appliance_detailed,
        calibrate_appliance_quick,
        calibrate_appliance_simple,
        deserialize_capabilities_map,
        extract_profile_metadata,
        save_profile_backup,
        serialize_capabilities_map,
    )
    from ifb_washer_local.const import (  # type: ignore[import-not-found, import-untyped]
        DIAL_SIDES_BY_FAMILY,
        MACHINE_TYPE_LABELS,
        MODELS_BY_FAMILY,
        PROGRAM_CAPABILITIES_FRONT_LOAD,
        PROGRAM_CAPABILITIES_TOP_LOAD,
        PROGRAM_CAPABILITIES_WASHER_DRYER,
    )

from .const import (
    CONF_CALIBRATED_PROFILE,
    CONF_CUSTOM_MODEL,
    CONF_FAMILY,
    CONF_MAC_ADDRESS,
    CONF_MODEL,
    CONF_SCAN_INTERVAL_RUNNING,
    CONF_SCAN_INTERVAL_STANDBY,
    DEFAULT_FAMILY,
    DEFAULT_SCAN_INTERVAL_RUNNING,
    DEFAULT_SCAN_INTERVAL_STANDBY,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def _normalize_mac(mac: str) -> str:
    """Return a MAC address as a lowercase 12-character hex string with no separators."""
    return mac.lower().replace(":", "").replace("-", "")


async def _async_get_mac_from_arp(hass: Any, ip: str) -> str:
    """Look up a device's MAC address from the Linux ARP table for a given IP.

    Reads /proc/net/arp which is always present on Linux (HA OS / Container).
    Returns an empty string if the IP is not found or the entry is incomplete.
    """
    def _read_arp() -> str:
        try:
            with open("/proc/net/arp", encoding="utf-8") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 4 and parts[0] == ip:
                        mac = parts[3]
                        if mac not in ("00:00:00:00:00:00", ""):
                            return mac.lower()
        except Exception:
            pass
        return ""

    try:
        return await hass.async_add_executor_job(_read_arp)
    except Exception:
        return ""

MACHINE_TYPE_OPTIONS = [
    selector.SelectOptionDict(
        value=ApplianceFamily.WASHER_DRYER,
        label="Washer Dryer Refresher",
    ),
    selector.SelectOptionDict(
        value=ApplianceFamily.FRONT_LOAD,
        label="Front Load Washer",
    ),
    selector.SelectOptionDict(
        value=ApplianceFamily.TOP_LOAD_SMART,
        label="Top Load Washer",
    ),
]


def _get_model_options_for_family(family: str) -> list[selector.SelectOptionDict]:
    """Get list of model options from ifb_washer_models catalog."""
    try:
        from ifb_washer_models import get_lookup
        lookup = get_lookup()
        models = lookup.all_models

        filtered: list[str] = []
        for m in models:
            arch = str(m.archetype).lower()
            name = m.model_name.lower()
            if family == ApplianceFamily.WASHER_DRYER:
                if "washer_dryer" in arch or "dry" in arch or "turbodry" in name or "wd" in name:
                    filtered.append(m.model_name)
            elif family == ApplianceFamily.TOP_LOAD_SMART:
                if "top_load" in arch or "tl" in arch:
                    filtered.append(m.model_name)
            else:  # FRONT_LOAD
                if not (
                    "washer_dryer" in arch
                    or "dry" in arch
                    or "turbodry" in name
                    or "wd" in name
                    or "top_load" in arch
                    or "tl" in arch
                ):
                    filtered.append(m.model_name)

        if not filtered:
            filtered = MODELS_BY_FAMILY.get(family, [])

        unique_models = sorted(list(dict.fromkeys(filtered)))
        options = [selector.SelectOptionDict(value=m, label=m) for m in unique_models]
        options.append(
            selector.SelectOptionDict(value="custom", label="Other / Custom Model...")
        )
        return options
    except Exception:
        model_list = MODELS_BY_FAMILY.get(family, ["custom"])
        return [
            selector.SelectOptionDict(
                value=m,
                label="Other / Custom Model..." if m == "custom" else m,
            )
            for m in model_list
        ]


class IFBWasherConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for IFB Washer Local."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow state."""
        self._host: str = ""
        self._port: int = DEFAULT_PORT
        self._name: str | None = None
        self._family: str = DEFAULT_FAMILY
        self._model: str = "Executive Plus VX WD 8.5/6.5"
        self._custom_model: str = ""
        self._client: IFBWasherClient | None = None
        self._initial_state: WasherState | None = None
        self._phase1_code: int = 12
        self._phase1_side: str = "left"
        self._calibrated_profile: dict[str, Any] | None = None
        self._mac_address: str = ""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Enter local IP address and test connection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = int(user_input.get(CONF_PORT, DEFAULT_PORT))
            self._name = user_input.get(CONF_NAME, "").strip() or None

            # Prevent duplicate entries for the same host IP without locking in-progress retries
            await self.async_set_unique_id(host, raise_on_progress=False)
            self._abort_if_unique_id_configured()

            # Test connection to the machine's Gainspan web server
            session = async_get_clientsession(self.hass)
            client = IFBWasherClient(host=host, port=port, session=session, timeout=5.0)

            try:
                state = await client.get_state()
            except (IFBTimeoutError, IFBConnectionError):
                errors["base"] = "cannot_connect"
            except IFBError:
                errors["base"] = "invalid_response"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error connecting to IFB washer at %s", host)
                errors["base"] = "unknown"
            else:
                self._host = host
                self._port = port
                self._client = client
                self._initial_state = state
                # Try to discover the device MAC from the system ARP table
                self._mac_address = await _async_get_mac_from_arp(self.hass, host)
                return await self.async_step_machine_type()

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=65535, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(CONF_NAME): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_machine_type(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose machine category using IFB official terminology."""
        if user_input is not None:
            self._family = user_input[CONF_FAMILY]
            return await self.async_step_model()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_FAMILY, default=ApplianceFamily.WASHER_DRYER
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=MACHINE_TYPE_OPTIONS,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="machine_type",
            data_schema=schema,
        )

    async def async_step_model(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select exact model from the family's catalog."""
        options = await self.hass.async_add_executor_job(
            _get_model_options_for_family, self._family
        )

        if user_input is not None:
            chosen = user_input[CONF_MODEL]
            if chosen == "custom":
                return await self.async_step_custom_model_text()
            self._model = chosen
            return await self.async_step_verify_initial()

        default_model = options[0]["value"] if options else "custom"
        schema = vol.Schema(
            {
                vol.Required(CONF_MODEL, default=default_model): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="model",
            data_schema=schema,
            description_placeholders={
                "type_name": MACHINE_TYPE_LABELS.get(self._family, "Washing Machine")
            },
        )

    async def async_step_custom_model_text(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 3b: Enter custom model name."""
        if user_input is not None:
            custom_name = user_input.get(CONF_CUSTOM_MODEL, "").strip()
            self._model = custom_name or "Custom IFB Model"
            self._custom_model = custom_name
            return await self.async_step_verify_initial()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_CUSTOM_MODEL, default="WD Executive ZXS"
                ): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
            }
        )

        return self.async_show_form(
            step_id="custom_model_text",
            data_schema=schema,
        )

    async def async_step_verify_initial(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm current program reported by the appliance with auto power-on."""
        if self._client:
            try:
                state = await self._client.get_state()
                self._initial_state = state
                if not state.is_powered_on:
                    _LOGGER.info("IFB washer display is off; sending power on command to wake panel")
                    state = await self._client.power_on()
                    self._initial_state = state
            except Exception as err:
                _LOGGER.debug("Initial power check / auto wake exception: %s", err)

        prog_map = FAMILY_PROGRAM_MATRICES.get(
            self._family, PROGRAM_CODES_WASHER_DRYER
        )
        curr_code = (
            self._initial_state.program_code
            if self._initial_state and self._initial_state.program_code in prog_map
            else list(prog_map.keys())[0]
        )
        curr_name = prog_map.get(curr_code, f"Program {curr_code}")

        return self.async_show_menu(
            step_id="verify_initial",
            menu_options=["verify_phase1", "retry_power", "skip_verification"],
            description_placeholders={
                "active_name": curr_name,
                "active_code": str(curr_code),
            },
        )

    async def async_step_retry_power(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Retry sending power-on command to wake the appliance display."""
        if self._client:
            try:
                await self._client.power_on()
                await asyncio.sleep(0.5)
                self._initial_state = await self._client.get_state()
            except Exception as err:
                _LOGGER.debug("Retry power on exception: %s", err)
        return await self.async_step_verify_initial()

    async def async_step_verify_phase1(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 4b: Same-side verification test."""
        prog_map = FAMILY_PROGRAM_MATRICES.get(
            self._family, PROGRAM_CODES_WASHER_DRYER
        )
        right_codes, left_codes = DIAL_SIDES_BY_FAMILY.get(
            self._family, ([1, 2, 3, 4, 5, 6, 7], [8, 9, 10, 11, 12, 13, 14, 15])
        )

        curr_code = (
            self._initial_state.program_code
            if self._initial_state and self._initial_state.program_code in prog_map
            else list(prog_map.keys())[0]
        )

        # Determine which side the current program is on, and pick another on the SAME side
        if curr_code in left_codes:
            self._phase1_side = "left"
            candidates = [c for c in left_codes if c != curr_code and c in prog_map]
            test_code = candidates[0] if candidates else curr_code
        else:
            self._phase1_side = "right"
            candidates = [c for c in right_codes if c != curr_code and c in prog_map]
            test_code = candidates[0] if candidates else curr_code

        self._phase1_code = test_code
        target_name = prog_map.get(test_code, f"Program {test_code}")

        # Probe physical machine with same-side program safely
        try:
            if self._client:
                curr_state = await self._client.get_state()
                if curr_state.is_running or curr_state.is_paused:
                    _LOGGER.warning(
                        "IFB Washer at %s is actively running or paused; skipping Phase 1 verification probe to protect wash cycle",
                        self._host,
                    )
                else:
                    await self._client.select_program(
                        test_code,
                        spin_code=curr_state.spin_speed_code,
                        temp_code=curr_state.temperature_code,
                    )
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.debug("Phase 1 verification probe exception: %s", err)

        return self.async_show_menu(
            step_id="verify_phase1",
            menu_options=["verify_phase2", "skip_verification"],
            description_placeholders={
                "target_name": target_name,
                "target_code": str(test_code),
            },
        )

    async def async_step_verify_phase2(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Opposite-side verification test."""
        prog_map = FAMILY_PROGRAM_MATRICES.get(
            self._family, PROGRAM_CODES_WASHER_DRYER
        )
        right_codes, left_codes = DIAL_SIDES_BY_FAMILY.get(
            self._family, ([1, 2, 3, 4, 5, 6, 7], [8, 9, 10, 11, 12, 13, 14, 15])
        )

        # Pick from the OPPOSITE side of Phase 1
        if self._phase1_side == "left":
            candidates = [c for c in right_codes if c in prog_map]
        else:
            candidates = [c for c in left_codes if c in prog_map]

        test_code = candidates[0] if candidates else list(prog_map.keys())[-1]
        target_name = prog_map.get(test_code, f"Program {test_code}")

        # Probe physical machine with opposite-side program safely
        try:
            if self._client:
                curr_state = await self._client.get_state()
                if curr_state.is_running or curr_state.is_paused:
                    _LOGGER.warning(
                        "IFB Washer at %s is actively running or paused; skipping Phase 2 verification probe to protect wash cycle",
                        self._host,
                    )
                else:
                    await self._client.select_program(
                        test_code,
                        spin_code=curr_state.spin_speed_code,
                        temp_code=curr_state.temperature_code,
                    )
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.debug("Phase 2 verification probe exception: %s", err)

        return self.async_show_menu(
            step_id="verify_phase2",
            menu_options=["finish_verification", "skip_verification"],
            description_placeholders={
                "target_name": target_name,
                "target_code": str(test_code),
            },
        )

    async def async_step_finish_verification(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Finish dial verification and prompt for hardware capability calibration."""
        return await self.async_step_calibrate()

    async def async_step_skip_verification(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Skip dial verification and prompt for hardware capability calibration."""
        return await self.async_step_calibrate()

    async def async_step_calibrate(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Prompt user to choose hardware capability calibration mode."""
        return self.async_show_menu(
            step_id="calibrate",
            menu_options=[
                "calibrate_standard",
                "calibrate_quick",
                "calibrate_simple",
                "calibrate_detailed",
            ],
            description_placeholders={
                "model_name": self._model,
            },
        )

    async def async_step_calibrate_standard(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Skip live probing and use pre-defined model catalog profile."""
        self._calibrated_profile = None
        return self._create_entry()

    async def async_step_calibrate_quick(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Run quick ~2m hardware calibration on core daily programs."""
        return await self._start_calibration("quick")

    async def async_step_calibrate_simple(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Run simple ~4-5 min model-constrained calibration across all dial positions."""
        return await self._start_calibration("simple")

    async def async_step_calibrate_detailed(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Run full ~15 min detailed brute-force hardware calibration across all dial positions."""
        return await self._start_calibration("detailed")

    async def _start_calibration(self, mode: str) -> ConfigFlowResult:
        """Start async calibration task with Home Assistant native progress screen."""
        return self.async_show_progress(
            step_id="calibrate_progress",
            progress_action="calibrate_progress",
            progress_task=self.hass.async_create_task(self._async_run_calibration_task(mode)),
        )

    async def _async_run_calibration_task(self, mode: str) -> None:
        """Execute hardware probe task."""
        if self._client is None:
            session = async_get_clientsession(self.hass)
            self._client = IFBWasherClient(host=self._host, port=self._port, session=session)

        # Ensure appliance is awake and powered ON
        try:
            await self._client.power_on()
            await asyncio.sleep(0.5)
        except Exception:
            pass

        prog_map = FAMILY_PROGRAM_MATRICES.get(
            self._family, PROGRAM_CODES_WASHER_DRYER
        )
        is_wd = self._family in (ApplianceFamily.WASHER_DRYER, "washer_dryer")

        if self._family == ApplianceFamily.FRONT_LOAD:
            base_caps_map = PROGRAM_CAPABILITIES_FRONT_LOAD
        elif self._family == ApplianceFamily.TOP_LOAD_SMART:
            base_caps_map = PROGRAM_CAPABILITIES_TOP_LOAD
        else:
            base_caps_map = PROGRAM_CAPABILITIES_WASHER_DRYER

        try:
            st = await self._client.get_state()
            if not st.is_running and not st.is_paused:
                if mode == "detailed":
                    result = await calibrate_appliance_detailed(
                        self._client,
                        prog_map,
                        base_caps_map,
                        is_washer_dryer=is_wd,
                    )
                elif mode == "simple":
                    result = await calibrate_appliance_simple(
                        self._client,
                        prog_map,
                        base_caps_map,
                        is_washer_dryer=is_wd,
                    )
                else:
                    result = await calibrate_appliance_quick(
                        self._client,
                        prog_map,
                        base_caps_map,
                        is_washer_dryer=is_wd,
                    )
                self._calibrated_profile = serialize_capabilities_map(
                    result,
                    mode=mode,
                    model=self._model,
                    family=str(self._family),
                )
                _LOGGER.info(
                    "Calibrated %d programs during config flow for IFB %s (mode: %s)",
                    len(result),
                    self._model,
                    mode,
                )
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.warning("Appliance calibration error during setup: %s", exc)

    async def async_step_calibrate_progress(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle completion of the calibration progress task."""
        return self.async_show_progress_done(next_step_id="finish_calibration")

    async def async_step_finish_calibration(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create entry once calibration completes."""
        return self._create_entry()

    async def async_step_custom(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manual / custom configuration step."""
        if user_input is not None:
            self._family = ApplianceFamily.CUSTOM
            self._model = "Custom Dial Model"
            return await self.async_step_calibrate()

        return self.async_show_form(
            step_id="custom",
            data_schema=vol.Schema({}),
        )

    def _create_entry(self) -> ConfigFlowResult:
        """Create the config entry."""
        title = self._name or f"IFB {self._model} ({self._host})"
        data: dict[str, Any] = {
            CONF_HOST: self._host,
            CONF_PORT: self._port,
            CONF_FAMILY: self._family,
            CONF_MODEL: self._model,
            CONF_CUSTOM_MODEL: self._custom_model,
        }
        if self._name:
            data[CONF_NAME] = self._name
        if self._mac_address:
            data[CONF_MAC_ADDRESS] = self._mac_address
        if self._calibrated_profile:
            data[CONF_CALIBRATED_PROFILE] = self._calibrated_profile

        return self.async_create_entry(
            title=title,
            data=data,
        )

    async def async_step_dhcp(
        self, discovery_info: DhcpServiceInfo
    ) -> ConfigFlowResult:
        """Handle DHCP discovery.

        When HA sees a DHCP lease whose MAC matches the GainSpan OUI (20:F8:5E),
        this handler fires. If an existing entry has a matching MAC address stored,
        the host IP is updated in-place on both the config entry and the running
        coordinator so the integration reconnects without a full reload.
        """
        discovered_ip = discovery_info.ip
        discovered_mac = discovery_info.macaddress.lower()

        _LOGGER.debug(
            "DHCP discovery: IFB washer candidate at %s (MAC %s)",
            discovered_ip,
            discovered_mac,
        )

        # Try to match against an existing configured entry by stored MAC address
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            stored_mac = entry.data.get(CONF_MAC_ADDRESS, "").lower()
            if not stored_mac:
                continue
            if _normalize_mac(stored_mac) == _normalize_mac(discovered_mac):
                existing_host = entry.data.get(CONF_HOST, "")
                if existing_host == discovered_ip:
                    _LOGGER.debug(
                        "DHCP: IFB washer at %s is already configured with correct IP — no update needed",
                        discovered_ip,
                    )
                    return self.async_abort(reason="already_configured")

                _LOGGER.info(
                    "DHCP: IFB washer MAC %s changed IP %s -> %s — updating config entry",
                    stored_mac,
                    existing_host,
                    discovered_ip,
                )
                # Update the stored host in the config entry
                new_data = dict(entry.data)
                new_data[CONF_HOST] = discovered_ip
                self.hass.config_entries.async_update_entry(entry, data=new_data)

                # Update the running coordinator's client host in-place
                coordinator = self.hass.data.get(DOMAIN, {}).get(entry.entry_id)
                if coordinator is not None:
                    coordinator.client.host = discovered_ip
                    _LOGGER.info(
                        "DHCP: Coordinator client host updated to %s — requesting refresh",
                        discovered_ip,
                    )
                    self.hass.async_create_task(coordinator.async_request_refresh())

                return self.async_abort(reason="already_configured")

        # No matching entry: start a fresh setup flow pre-populated with the discovered IP
        self._host = discovered_ip
        self._mac_address = discovered_mac
        await self.async_set_unique_id(discovered_ip, raise_on_progress=False)
        self._abort_if_unique_id_configured()
        return await self.async_step_user()

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlow:
        """Get options flow for this entry."""
        return IFBWasherOptionsFlowHandler(config_entry)


class IFBWasherOptionsFlowHandler(OptionsFlow):
    """Handle options for IFB Washer Local."""

    def __init__(self, config_entry: ConfigEntry | None = None) -> None:
        """Initialize options flow safely without writing to read-only property."""
        self._entry_ref = config_entry

    @property
    def _entry(self) -> ConfigEntry:
        """Get the active config entry."""
        if self._entry_ref is not None:
            return self._entry_ref
        try:
            if hasattr(self, "config_entry") and self.config_entry is not None:
                return self.config_entry
        except (ValueError, AttributeError):
            pass
        raise RuntimeError("No config entry found in options flow")

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage integration options."""
        entry = self._entry
        coordinator = self.hass.data.get(DOMAIN, {}).get(entry.entry_id)

        current_name = entry.data.get(CONF_NAME, "")
        current_model = entry.options.get(
            CONF_MODEL,
            entry.data.get(CONF_MODEL, "WD Executive ZXS"),
        )
        current_standby = entry.options.get(
            CONF_SCAN_INTERVAL_STANDBY, DEFAULT_SCAN_INTERVAL_STANDBY
        )
        current_running = entry.options.get(
            CONF_SCAN_INTERVAL_RUNNING, DEFAULT_SCAN_INTERVAL_RUNNING
        )

        if user_input is not None:
            new_name = user_input.get(CONF_NAME, "").strip() or None
            new_model = user_input.get(CONF_MODEL, current_model).strip()

            # Update entry data with new name and model if changed
            new_data = dict(entry.data)
            new_data[CONF_MODEL] = new_model
            if new_name:
                new_data[CONF_NAME] = new_name
            else:
                new_data.pop(CONF_NAME, None)

            new_title = new_name or f"IFB {new_model} ({entry.data.get(CONF_HOST)})"
            self.hass.config_entries.async_update_entry(
                entry,
                title=new_title,
                data=new_data,
            )

            self._options_data = {
                CONF_MODEL: new_model,
                CONF_SCAN_INTERVAL_STANDBY: user_input[CONF_SCAN_INTERVAL_STANDBY],
                CONF_SCAN_INTERVAL_RUNNING: user_input[CONF_SCAN_INTERVAL_RUNNING],
            }

            cal_action = user_input.get("calibration_action", "none")
            if cal_action in ("quick", "simple", "detailed"):
                if coordinator:
                    return self.async_show_progress(
                        step_id="calibrate_progress",
                progress_action="calibrate_progress",
                        progress_task=self.hass.async_create_task(
                            coordinator.async_calibrate(mode=cal_action)
                        ),
                    )
            elif cal_action in ("manage_profile", "export", "restore"):
                return await self.async_step_manage_profile()
            elif cal_action == "reset":
                if coordinator:
                    await coordinator.async_clear_profile()
                else:
                    new_data = dict(entry.data)
                    new_data.pop(CONF_CALIBRATED_PROFILE, None)
                    self.hass.config_entries.async_update_entry(entry, data=new_data)

            return self.async_create_entry(
                title="",
                data=self._options_data,
            )

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_NAME, default=current_name
                ): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Required(
                    CONF_MODEL, default=current_model
                ): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Optional(
                    CONF_SCAN_INTERVAL_STANDBY, default=current_standby
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=5, max=120, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="seconds"
                    )
                ),
                vol.Optional(
                    CONF_SCAN_INTERVAL_RUNNING, default=current_running
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=2, max=30, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="seconds"
                    )
                ),
                vol.Optional(
                    "calibration_action", default="none"
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value="none", label="Keep Current Profile"),
                            selector.SelectOptionDict(value="manage_profile", label="Manage / Export / Import Profile (JSON)"),
                            selector.SelectOptionDict(value="quick", label="Run Quick Calibration (~2m)"),
                            selector.SelectOptionDict(value="simple", label="Run Simple Calibration (~4-5m)"),
                            selector.SelectOptionDict(value="detailed", label="Run Detailed Calibration (~15m)"),
                            selector.SelectOptionDict(value="reset", label="Reset to Standard Catalog Defaults"),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
        )

    async def async_step_manage_profile(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Unified Profile Manager: select from disk, upload JSON file, or live-edit active profile."""
        errors: dict[str, str] = {}
        entry = self._entry
        coordinator = self.hass.data.get(DOMAIN, {}).get(entry.entry_id)
        model_name = entry.options.get(CONF_MODEL) or entry.data.get(CONF_MODEL) or "IFB Washing Machine"
        clean_model = model_name.lower().replace(" ", "_").replace("/", "_").replace(".", "_")
        backup_file = f"/config/ifb_washer_profiles/{clean_model}_profile.json"

        if user_input is not None:
            raw_text = user_input.get("profile_json", "").strip()
            file_path = user_input.get("profile_file")

            # Handle file upload if provided
            if file_path:
                try:
                    def _read_file(p: str) -> str:
                        with open(p, "r", encoding="utf-8") as f:
                            return f.read()
                    raw_text = await self.hass.async_add_executor_job(_read_file, file_path)
                except Exception as file_err:
                    _LOGGER.warning("Could not read uploaded profile file: %s", file_err)

            if raw_text:
                try:
                    parsed = json.loads(raw_text)
                    if not isinstance(parsed, dict):
                        raise ValueError("JSON root must be an object")
                    if coordinator:
                        await coordinator.async_restore_profile(parsed)
                    else:
                        caps = deserialize_capabilities_map(parsed)
                        if not caps:
                            raise ValueError("No valid program capabilities found in profile")
                        new_data = dict(entry.data)
                        new_data[CONF_CALIBRATED_PROFILE] = serialize_capabilities_map(
                            caps,
                            mode="imported",
                            model=model_name,
                        )
                        self.hass.config_entries.async_update_entry(entry, data=new_data)

                    return self.async_create_entry(
                        title="",
                        data=getattr(self, "_options_data", {}),
                    )
                except Exception as exc:
                    _LOGGER.warning("Failed to parse/apply profile JSON: %s", exc)
                    errors["profile_json"] = "invalid_profile_json"
            else:
                return self.async_create_entry(
                    title="",
                    data=getattr(self, "_options_data", {}),
                )

        # Build initial JSON display
        cal_data = entry.options.get(CONF_CALIBRATED_PROFILE) or entry.data.get(CONF_CALIBRATED_PROFILE)
        if cal_data and isinstance(cal_data, dict):
            if "capabilities" in cal_data:
                profile_json = json.dumps(cal_data, indent=2)
            else:
                caps = deserialize_capabilities_map(cal_data)
                envelope = serialize_capabilities_map(
                    caps,
                    mode="simple",
                    model=model_name,
                    family=str(getattr(coordinator, "appliance_family", "washer_dryer")),
                )
                profile_json = json.dumps(envelope, indent=2)
        elif coordinator and isinstance(getattr(coordinator, "calibrated_caps", None), dict) and coordinator.calibrated_caps:
            meta_mode = "simple"
            if isinstance(getattr(coordinator, "calibrated_meta", None), dict):
                meta_mode = str(coordinator.calibrated_meta.get("calibration_mode", "simple"))
            envelope = serialize_capabilities_map(
                coordinator.calibrated_caps,
                mode=meta_mode,
                model=model_name,
                family=str(getattr(coordinator, "appliance_family", "washer_dryer")),
            )
            profile_json = json.dumps(envelope, indent=2)
        else:
            prog_map = getattr(coordinator, "program_map", PROGRAM_CODES_WASHER_DRYER)
            base_caps = {code: getattr(coordinator, "get_program_capabilities", lambda c: None)(code) for code in prog_map}
            valid_caps = {k: v for k, v in base_caps.items() if v is not None}
            envelope = serialize_capabilities_map(
                valid_caps,
                mode="catalog_default",
                model=model_name,
                family=str(getattr(coordinator, "appliance_family", "washer_dryer")),
            )
            profile_json = json.dumps(envelope, indent=2)

        # Auto-save export backup copy
        try:
            if hasattr(self.hass, "config") and isinstance(getattr(self.hass.config, "config_dir", None), str):
                config_dir = self.hass.config.config_dir
                parsed_env = json.loads(profile_json)
                caps_to_save = deserialize_capabilities_map(parsed_env)
                if caps_to_save:
                    await self.hass.async_add_executor_job(
                        save_profile_backup,
                        config_dir,
                        caps_to_save,
                        "exported",
                        model_name,
                        str(getattr(coordinator, "appliance_family", "washer_dryer")),
                    )
        except Exception as exc:
            _LOGGER.debug("Could not auto-save export profile: %s", exc)

        # Discovered saved profile files on disk
        saved_files: list[str] = []
        try:
            if hasattr(self.hass, "config") and isinstance(getattr(self.hass.config, "config_dir", None), str):
                config_dir = self.hass.config.config_dir
                if coordinator and hasattr(coordinator, "async_list_profile_files"):
                    saved_files = await coordinator.async_list_profile_files()
                else:
                    saved_files = await self.hass.async_add_executor_job(list_profile_files, config_dir)
        except Exception:
            pass

        file_options = [
            selector.SelectOptionDict(value="active", label="Active Profile (Current)"),
        ]
        for f in saved_files:
            file_options.append(selector.SelectOptionDict(value=f, label=f"/config/ifb_washer_profiles/{f}"))

        schema_dict: dict[Any, Any] = {}
        if saved_files:
            schema_dict[vol.Optional("saved_profile", default="active")] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=file_options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )

        schema_dict[vol.Optional("profile_file")] = selector.FileSelector(
            selector.FileSelectorConfig(accept=".json")
        )
        schema_dict[vol.Optional("profile_json", default=profile_json)] = selector.TextSelector(
            selector.TextSelectorConfig(
                multiline=True,
                type=selector.TextSelectorType.TEXT,
            )
        )

        return self.async_show_form(
            step_id="manage_profile",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
            description_placeholders={"backup_file": backup_file},
        )

    async def async_step_export_profile(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Alias for manage_profile."""
        return await self.async_step_manage_profile(user_input)

    async def async_step_restore_profile(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Alias for manage_profile."""
        return await self.async_step_manage_profile(user_input)

    async def async_step_calibrate_progress(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle completion of calibration progress in options flow."""
        return self.async_show_progress_done(next_step_id="finish_options")

    async def async_step_finish_options(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Finalize options update once calibration task completes."""
        return self.async_create_entry(
            title="",
            data=getattr(self, "_options_data", {}),
        )


