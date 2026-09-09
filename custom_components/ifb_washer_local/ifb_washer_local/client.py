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
    FIXED_CMD_POWER_ON,
    FIXED_CMD_POWER_OFF,
    GAINSPAN_PROFILE_ENDPOINT,
    HIL_OPTION_ANTI_CREASE,
    HIL_OPTION_AROMA,
    HIL_OPTION_DELAY,
    HIL_OPTION_DRY,
    HIL_OPTION_ECO,
    HIL_OPTION_EXTRA_RINSE,
    HIL_OPTION_HOT_RINSE,
    HIL_OPTION_PRE_WASH,
    HIL_OPTION_RINSE_HOLD,
    HIL_OPTION_SOAK,
    HIL_OPTION_TEMP,
    HIL_OPTION_TIME_SAVER,
    SPIN_SPEED_CODE_TO_RPM,
    SPIN_SPEED_OPTIONS,
    TEMPERATURE_CODE_TO_CELSIUS,
    TEMPERATURE_OPTIONS,
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
        self._lock = asyncio.Lock()

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the aiohttp ClientSession."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            self._owns_session = True
        return self._session

    async def _send_raw_command(self, payload: bytes) -> bytes:
        """Send raw binary command to the GainSpan HTTP profile endpoint."""
        async with self._lock:
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

    async def select_program(
        self,
        program_code: int,
        spin_code: int = 6,
        temp_code: int = 4,
    ) -> WasherState:
        """Select a wash program and return the updated state."""
        cmd_pkt = build_program_selection(program_code, spin_code=spin_code, temp_code=temp_code)
        await self._send_raw_command(cmd_pkt)
        # Allow MCU to settle relays and update telemetry registers (typically 0.8s - 1.2s)
        for _ in range(6):
            await asyncio.sleep(0.4)
            state = await self.get_state()
            if state.program_code == program_code:
                return state
        return state

    async def set_child_lock(self, enable: bool) -> WasherState:
        """Enable or disable the child lock and return the updated state."""
        cmd_pkt = build_child_lock_command(enable)
        await self._send_raw_command(cmd_pkt)
        await asyncio.sleep(0.3)
        return await self.get_state()

    async def set_spin_speed(
        self,
        spin_code: int,
        program_code: Optional[int] = None,
        temp_code: Optional[int] = None,
    ) -> WasherState:
        """Set the spin speed option using synchronized program parameters."""
        prog = program_code
        temp = temp_code
        if prog is None or temp is None:
            current_state = await self.get_state()
            if prog is None:
                prog = current_state.program_code
            if temp is None:
                temp = current_state.temperature_code if current_state.temperature_code else 4

        cmd_pkt = build_program_selection(prog, spin_code=spin_code, temp_code=temp)
        await self._send_raw_command(cmd_pkt)
        for _ in range(6):
            await asyncio.sleep(0.3)
            state = await self.get_state()
            if state.spin_speed_code == spin_code or state.spin_speed_name == SPIN_SPEED_OPTIONS.get(spin_code):
                return state
        return state

    async def set_temperature(
        self,
        temp_code: int,
        program_code: Optional[int] = None,
        spin_code: Optional[int] = None,
    ) -> WasherState:
        """Set the temperature option using synchronized program parameters."""
        prog = program_code
        spin = spin_code
        if prog is None or spin is None:
            current_state = await self.get_state()
            if prog is None:
                prog = current_state.program_code
            if spin is None:
                spin = current_state.spin_speed_code if current_state.spin_speed_code else 6

        cmd_pkt = build_program_selection(prog, spin_code=spin, temp_code=temp_code)
        await self._send_raw_command(cmd_pkt)
        for _ in range(6):
            await asyncio.sleep(0.3)
            state = await self.get_state()
            if state.temperature_code == temp_code or state.temperature_name == TEMPERATURE_OPTIONS.get(temp_code):
                return state
        return state

    async def set_delay_start(self, delay_code: int) -> WasherState:
        """Set the delay start option code (0 for No Delay, 1 for 30m, 2 for 1h, 4 for 2h ...)."""
        cmd_pkt = build_user_option_command(HIL_OPTION_DELAY, delay_code)
        await self._send_raw_command(cmd_pkt)
        expected_mins = 0 if delay_code == 0 else (30 if delay_code == 1 else (delay_code // 2) * 60)
        for _ in range(4):
            await asyncio.sleep(0.3)
            state = await self.get_state()
            if abs(state.delay_start_minutes - expected_mins) <= 2:
                return state
        return state

    async def set_extra_rinse(self, count: int) -> WasherState:
        """Set the extra rinse count (0 to 3)."""
        cmd_pkt = build_user_option_command(HIL_OPTION_EXTRA_RINSE, count)
        await self._send_raw_command(cmd_pkt)
        for _ in range(4):
            await asyncio.sleep(0.3)
            state = await self.get_state()
            if state.extra_rinse == count:
                return state
        return state

    async def set_dry_mode(self, dry_code: int) -> WasherState:
        """Set the dryer mode option code (0 for Off, 1 for Cupboard Dry, etc.)."""
        cmd_pkt = build_user_option_command(HIL_OPTION_DRY, dry_code)
        await self._send_raw_command(cmd_pkt)
        for _ in range(4):
            await asyncio.sleep(0.3)
            state = await self.get_state()
            if state.dry_mode_code == dry_code:
                return state
        return state

    async def set_feature_toggle(self, hil_id: int, enable: bool) -> WasherState:
        """Toggle an operational modifier feature on or off."""
        val = 1 if enable else 0
        cmd_pkt = build_user_option_command(hil_id, val)
        await self._send_raw_command(cmd_pkt)
        await asyncio.sleep(0.4)
        return await self.get_state()

    async def set_prewash(self, enable: bool) -> WasherState:
        """Enable or disable pre-wash."""
        return await self.set_feature_toggle(HIL_OPTION_PRE_WASH, enable)

    async def set_soak(self, enable: bool) -> WasherState:
        """Enable or disable soak."""
        return await self.set_feature_toggle(HIL_OPTION_SOAK, enable)

    async def set_rinse_hold(self, enable: bool) -> WasherState:
        """Enable or disable rinse hold."""
        return await self.set_feature_toggle(HIL_OPTION_RINSE_HOLD, enable)

    async def set_time_saver(self, enable: bool) -> WasherState:
        """Enable or disable time saver."""
        return await self.set_feature_toggle(HIL_OPTION_TIME_SAVER, enable)

    async def set_hot_rinse(self, enable: bool) -> WasherState:
        """Enable or disable hot rinse."""
        return await self.set_feature_toggle(HIL_OPTION_HOT_RINSE, enable)

    async def set_eco(self, enable: bool) -> WasherState:
        """Enable or disable eco mode."""
        return await self.set_feature_toggle(HIL_OPTION_ECO, enable)

    async def set_steam(self, enable: bool) -> WasherState:
        """Enable or disable steam."""
        return await self.set_feature_toggle(HIL_OPTION_STEAM, enable)

    async def set_aroma(self, enable: bool) -> WasherState:
        """Enable or disable aroma."""
        return await self.set_feature_toggle(HIL_OPTION_AROMA, enable)

    async def set_anti_crease(self, enable: bool) -> WasherState:
        """Enable or disable anti-crease."""
        return await self.set_feature_toggle(HIL_OPTION_ANTI_CREASE, enable)

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

    async def power_on(self) -> WasherState:
        """Turn on the washing machine."""
        cmd_pkt = build_fixed_command(FIXED_CMD_POWER_ON)
        await self._send_raw_command(cmd_pkt)
        for _ in range(6):
            await asyncio.sleep(0.4)
            state = await self.get_state()
            if state.is_powered_on:
                return state
        return state

    async def power_off(self) -> WasherState:
        """Turn off the washing machine."""
        cmd_pkt = build_fixed_command(FIXED_CMD_POWER_OFF)
        await self._send_raw_command(cmd_pkt)
        for _ in range(6):
            await asyncio.sleep(0.4)
            state = await self.get_state()
            if not state.is_powered_on:
                return state
        return state

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
