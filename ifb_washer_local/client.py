"""Asynchronous LAN HTTP client for IFB front-load washing machines."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

import aiohttp

from .const import (
    DEFAULT_PORT,
    FIXED_CMD_CANCEL,
    FIXED_CMD_PAUSE,
    FIXED_CMD_PLAY,
    FIXED_CMD_POWER_OFF,
    GAINSPAN_PROFILE_ENDPOINT,
    HIL_OPTION_SPIN,
    HIL_OPTION_TEMP,
)
from .exceptions import (
    IFBConnectionError,
    IFBProtocolError,
    IFBTimeoutError,
)
from .protocol import (
    WasherState,
    build_child_lock_command,
    build_fixed_command,
    build_program_selection,
    build_status_query,
    build_user_option_command,
    parse_status_frame,
)

_LOGGER = logging.getLogger(__name__)


class IFBWasherClient:
    """Client for direct LAN communication with an IFB washing machine on port 80."""

    def __init__(
        self,
        host: str,
        port: int = DEFAULT_PORT,
        session: Optional[aiohttp.ClientSession] = None,
        timeout: float = 5.0,
        program_map: Optional[dict[int, str]] = None,
    ) -> None:
        """Initialize the client."""
        self.host = host
        self.port = port
        self.program_map = program_map
        self._session = session
        self._owns_session = session is None
        self._timeout = timeout

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the aiohttp ClientSession."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            self._owns_session = True
        return self._session

    async def _send_raw_command(self, payload: bytes) -> bytes:
        """Send raw binary command to the GainSpan HTTP profile endpoint."""
        session = await self._get_session()
        timestamp = int(time.time() * 1000)
        url = f"http://{self.host}:{self.port}{GAINSPAN_PROFILE_ENDPOINT}?t={timestamp}"
        headers = {"Content-Type": "multipart/form-data"}

        _LOGGER.debug("Sending raw command to %s: %s", self.host, payload.hex())
        try:
            async with session.post(
                url,
                data=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self._timeout),
            ) as response:
                if response.status != 200:
                    raise IFBConnectionError(f"HTTP request returned status {response.status}")
                data = await response.read()
                _LOGGER.debug("Received raw response from %s (%d bytes): %s", self.host, len(data), data.hex())
                return data
        except asyncio.TimeoutError as err:
            raise IFBTimeoutError(f"Timed out communicating with washer at {self.host}") from err
        except aiohttp.ClientError as err:
            raise IFBConnectionError(f"Network error connecting to washer at {self.host}: {err}") from err

    async def get_state(self) -> WasherState:
        """Query the washer and return the current state."""
        query_pkt = build_status_query()
        resp_bytes = await self._send_raw_command(query_pkt)
        state = parse_status_frame(resp_bytes, program_map=self.program_map)
        _LOGGER.debug(
            "Decoded telemetry from %s: prog='%s'(%d) state='%s'(%d) rem=%dm door_locked=%s raw[31]=%d rpm=%d temp=%d°C",
            self.host,
            state.program_name,
            state.program_code,
            state.state_name,
            state.state_code,
            state.remaining_minutes,
            state.door_locked,
            resp_bytes[31] if len(resp_bytes) > 31 else -1,
            state.motor_rpm,
            state.water_temperature_c,
        )
        return state

    async def select_program(self, program_code: int, spin_rpm: int = 1000, temp_c: int = 40) -> WasherState:
        """Select a wash program and return the updated state."""
        cmd_pkt = build_program_selection(program_code, spin_rpm, temp_c)
        await self._send_raw_command(cmd_pkt)
        await asyncio.sleep(0.3)
        return await self.get_state()

    async def set_child_lock(self, enable: bool) -> WasherState:
        """Enable or disable the child lock and return the updated state."""
        cmd_pkt = build_child_lock_command(enable)
        await self._send_raw_command(cmd_pkt)
        await asyncio.sleep(0.3)
        return await self.get_state()

    async def set_spin_speed(self, spin_code: int) -> WasherState:
        """Set the spin speed option code (e.g. 6 for 1000 RPM)."""
        cmd_pkt = build_user_option_command(HIL_OPTION_SPIN, spin_code)
        await self._send_raw_command(cmd_pkt)
        await asyncio.sleep(0.3)
        return await self.get_state()

    async def set_temperature(self, temp_code: int) -> WasherState:
        """Set the temperature option code (e.g. 4 for 40°C)."""
        cmd_pkt = build_user_option_command(HIL_OPTION_TEMP, temp_code)
        await self._send_raw_command(cmd_pkt)
        await asyncio.sleep(0.3)
        return await self.get_state()

    async def start(self) -> WasherState:
        """Start or resume the selected wash cycle."""
        cmd_pkt = build_fixed_command(FIXED_CMD_PLAY)
        await self._send_raw_command(cmd_pkt)
        await asyncio.sleep(0.5)
        return await self.get_state()

    async def pause(self) -> WasherState:
        """Pause the currently running wash cycle."""
        cmd_pkt = build_fixed_command(FIXED_CMD_PAUSE)
        await self._send_raw_command(cmd_pkt)
        await asyncio.sleep(0.5)
        return await self.get_state()

    async def cancel(self) -> WasherState:
        """Cancel the current wash cycle."""
        cmd_pkt = build_fixed_command(FIXED_CMD_CANCEL)
        await self._send_raw_command(cmd_pkt)
        await asyncio.sleep(0.5)
        return await self.get_state()

    async def power_off(self) -> None:
        """Turn off the washing machine."""
        cmd_pkt = build_fixed_command(FIXED_CMD_POWER_OFF)
        await self._send_raw_command(cmd_pkt)

    async def close(self) -> None:
        """Close the underlying session if owned by the client."""
        if self._owns_session and self._session is not None and not self._session.closed:
            await self._session.close()

    async def __aenter__(self) -> IFBWasherClient:
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        await self.close()
