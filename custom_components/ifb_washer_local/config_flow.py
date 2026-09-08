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
    IFBConnectionError,
    IFBError,
    IFBTimeoutError,
    IFBWasherClient,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default="192.168.0.100"): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
    }
)


class IFBWasherConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for IFB Washer Local."""

    VERSION = 1

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
                return self.async_create_entry(
                    title=f"IFB Washer ({host})",
                    data={
                        CONF_HOST: host,
                        CONF_PORT: port,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
