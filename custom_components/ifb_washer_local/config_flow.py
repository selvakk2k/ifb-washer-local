"""Config flow for IFB Washer Local integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ifb_washer_local import (
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
)
from ifb_washer_local.const import (
    DIAL_SIDES_BY_FAMILY,
    MACHINE_TYPE_LABELS,
    MODELS_BY_FAMILY,
)

from .const import (
    CONF_CUSTOM_MODEL,
    CONF_FAMILY,
    CONF_MODEL,
    DEFAULT_FAMILY,
    DEFAULT_SCAN_INTERVAL_RUNNING,
    DEFAULT_SCAN_INTERVAL_STANDBY,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

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


class IFBWasherConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for IFB Washer Local."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow state."""
        self._host: str = ""
        self._port: int = DEFAULT_PORT
        self._family: str = DEFAULT_FAMILY
        self._model: str = "WD Executive ZXS"
        self._custom_model: str = ""
        self._client: IFBWasherClient | None = None
        self._initial_state: WasherState | None = None
        self._phase1_code: int = 12
        self._phase1_side: str = "left"

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: Enter local IP address and test connection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = int(user_input.get(CONF_PORT, DEFAULT_PORT))

            # Prevent duplicate entries for the same host IP
            await self.async_set_unique_id(host)
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
                return await self.async_step_machine_type()

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default="192.168.0.100"): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=65535, mode=selector.NumberSelectorMode.BOX
                    )
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
        """Step 2: Choose machine category using IFB official terminology."""
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
        """Step 3: Select exact model from the family's catalog."""
        model_list = MODELS_BY_FAMILY.get(self._family, ["custom"])
        options = [
            selector.SelectOptionDict(
                value=m,
                label="Other / Custom Model..." if m == "custom" else m,
            )
            for m in model_list
        ]

        if user_input is not None:
            chosen = user_input[CONF_MODEL]
            if chosen == "custom":
                return await self.async_step_custom_model_text()
            self._model = chosen
            return await self.async_step_verify_phase1()

        default_model = model_list[0] if model_list else "custom"
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
            return await self.async_step_verify_phase1()

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

    async def async_step_verify_phase1(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 4a: Same-side verification test."""
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
        curr_name = prog_map.get(curr_code, f"Program {curr_code}")

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

        # Probe physical machine: send wake query first, pause 500ms, then select test program
        try:
            if self._client:
                await self._client.get_state()
                await asyncio.sleep(0.5)
                await self._client.select_program(test_code)
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.debug("Phase 1 verification probe exception: %s", err)

        is_top_load = self._family == ApplianceFamily.TOP_LOAD_SMART

        return self.async_show_menu(
            step_id="verify_phase1",
            menu_options=["verify_phase2", "skip_verification"],
            description_placeholders={
                "active_name": curr_name,
                "active_code": str(curr_code),
                "target_name": target_name,
                "target_code": str(test_code),
                "side_name": "same side" if not is_top_load else "primary group",
            },
        )

    async def async_step_verify_phase2(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 4b: Opposite-side verification test."""
        prog_map = FAMILY_PROGRAM_MATRICES.get(
            self._family, PROGRAM_CODES_WASHER_DRYER
        )
        right_codes, left_codes = DIAL_SIDES_BY_FAMILY.get(
            self._family, ([1, 2, 3, 4, 5, 6, 7], [8, 9, 10, 11, 12, 13, 14, 15])
        )

        # Pick from the OPPOSITE side of Phase 1
        if self._phase1_side == "left":
            candidates = [c for c in right_codes if c in prog_map]
            opp_side_name = "right side (opposite side)"
        else:
            candidates = [c for c in left_codes if c in prog_map]
            opp_side_name = "left side (opposite side)"

        test_code = candidates[0] if candidates else list(prog_map.keys())[-1]
        target_name = prog_map.get(test_code, f"Program {test_code}")

        # Probe physical machine with opposite-side program
        try:
            if self._client:
                await self._client.select_program(test_code)
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.debug("Phase 2 verification probe exception: %s", err)

        is_top_load = self._family == ApplianceFamily.TOP_LOAD_SMART

        return self.async_show_menu(
            step_id="verify_phase2",
            menu_options=["finish_verification", "skip_verification"],
            description_placeholders={
                "target_name": target_name,
                "target_code": str(test_code),
                "side_name": opp_side_name if not is_top_load else "opposite group",
            },
        )

    async def async_step_finish_verification(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Finish verification and complete setup."""
        return self._create_entry()

    async def async_step_skip_verification(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Skip dial verification and complete setup."""
        return self._create_entry()

    async def async_step_custom(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manual / custom configuration step."""
        if user_input is not None:
            self._family = ApplianceFamily.CUSTOM
            self._model = "Custom Dial Model"
            return self._create_entry()

        return self.async_show_form(
            step_id="custom",
            data_schema=vol.Schema({}),
        )

    def _create_entry(self) -> ConfigFlowResult:
        """Create the config entry."""
        title = f"IFB {self._model} ({self._host})"
        return self.async_create_entry(
            title=title,
            data={
                CONF_HOST: self._host,
                CONF_PORT: self._port,
                CONF_FAMILY: self._family,
                CONF_MODEL: self._model,
                CONF_CUSTOM_MODEL: self._custom_model,
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlow:
        """Get options flow for this entry."""
        return IFBWasherOptionsFlowHandler(config_entry)


class IFBWasherOptionsFlowHandler(OptionsFlow):
    """Handle options for IFB Washer Local."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage integration options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_standby = self.config_entry.options.get(
            "scan_interval_standby", DEFAULT_SCAN_INTERVAL_STANDBY
        )
        current_running = self.config_entry.options.get(
            "scan_interval_running", DEFAULT_SCAN_INTERVAL_RUNNING
        )
        current_model = self.config_entry.options.get(
            CONF_MODEL,
            self.config_entry.data.get(CONF_MODEL, "WD Executive ZXS"),
        )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_MODEL, default=current_model
                ): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Optional(
                    "scan_interval_standby", default=current_standby
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=5, max=120, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="seconds"
                    )
                ),
                vol.Optional(
                    "scan_interval_running", default=current_running
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=2, max=30, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="seconds"
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
        )
