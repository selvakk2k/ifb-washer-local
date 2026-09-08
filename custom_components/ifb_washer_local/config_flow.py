"""Config flow for IFB Washer Local integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ifb_washer_local import (
    DEFAULT_PORT,
    ApplianceFamily,
    IFBConnectionError,
    IFBError,
    IFBTimeoutError,
    IFBWasherClient,
    WasherState,
    detect_program_from_telemetry,
)

from .const import CONF_FAMILY, DEFAULT_FAMILY, DOMAIN

_LOGGER = logging.getLogger(__name__)

FAMILY_CHOICES = {
    ApplianceFamily.WASHER_DRYER: "Washer Dryer (WD Executive / ZXS Series)",
    ApplianceFamily.FRONT_LOAD: "Front Load (Senator / Executive Plus Series)",
    ApplianceFamily.TOP_LOAD_SMART: "Smart Top Load (SWID / SID Series) - Unverified",
    ApplianceFamily.AUTO_DETECT: "Auto-Detect from Telemetry",
    ApplianceFamily.CUSTOM: "Manual / Custom Configuration",
}


class IFBWasherConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for IFB Washer Local."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow state."""
        self._host: str = ""
        self._port: int = DEFAULT_PORT
        self._family: str = DEFAULT_FAMILY
        self._client: IFBWasherClient | None = None
        self._initial_state: WasherState | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = user_input.get(CONF_PORT, DEFAULT_PORT)

            # Prevent duplicate entries for the same host
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            # Test connection
            session = async_get_clientsession(self.hass)
            client = IFBWasherClient(host=host, port=port, session=session, timeout=5.0)

            try:
                state = await client.get_state()
            except IFBTimeoutError:
                errors["base"] = "cannot_connect"
            except IFBConnectionError:
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
                return await self.async_step_family()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_HOST, default="192.168.0.100"): str}),
            errors=errors,
        )


    async def async_step_family(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle appliance model family selection."""
        if user_input is not None:
            choice = user_input[CONF_FAMILY]
            if choice == ApplianceFamily.AUTO_DETECT:
                # Attempt telemetry signature auto-detection
                if self._initial_state:
                    detected = detect_program_from_telemetry(
                        duration_min=self._initial_state.remaining_minutes,
                        temp_c=self._initial_state.water_temperature_c,
                        spin_rpm=self._initial_state.motor_rpm,
                    )
                    if detected:
                        _LOGGER.info("Auto-detected telemetry signature for cycle: %s", detected)
                self._family = ApplianceFamily.WASHER_DRYER
                return await self.async_step_verify()
            if choice == ApplianceFamily.CUSTOM:
                self._family = ApplianceFamily.CUSTOM
                return await self.async_step_custom()

            self._family = choice
            return await self.async_step_verify()

        return self.async_show_form(
            step_id="family",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_FAMILY, default=ApplianceFamily.WASHER_DRYER
                    ): vol.In(FAMILY_CHOICES),
                }
            ),
        )

    async def async_step_verify(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Interactive visual verification test step."""
        test_code = 13 if self._family == ApplianceFamily.WASHER_DRYER else 1
        prog_name = "Mix / Daily"

        if user_input is not None:
            if user_input.get("skip_verification") or user_input.get("verified"):
                return self.async_create_entry(
                    title=f"IFB Washer ({self._host})",
                    data={
                        CONF_HOST: self._host,
                        CONF_PORT: self._port,
                        CONF_FAMILY: self._family,
                    },
                )
            return await self.async_step_custom()

        # Send test command to verify on physical front panel display
        try:
            if self._client:
                await self._client.select_program(test_code)
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.debug(
                "Verification probe skipped/failed (expected if appliance is actively washing): %s",
                err,
            )

        return self.async_show_form(
            step_id="verify",
            data_schema=vol.Schema(
                {
                    vol.Optional("verified", default=True): bool,
                    vol.Optional("skip_verification", default=False): bool,
                }
            ),
            description_placeholders={
                "program_name": prog_name,
                "program_code": str(test_code),
            },
        )

    async def async_step_custom(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manual / custom configuration step."""
        if user_input is not None:
            return self.async_create_entry(
                title=f"IFB Washer ({self._host})",
                data={
                    CONF_HOST: self._host,
                    CONF_PORT: self._port,
                    CONF_FAMILY: ApplianceFamily.CUSTOM,
                },
            )

        return self.async_show_form(
            step_id="custom",
            data_schema=vol.Schema({}),
        )

