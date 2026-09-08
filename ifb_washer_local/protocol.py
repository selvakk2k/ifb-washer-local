"""Protocol frame encoding, decoding, and checksum verification for IFB washing machines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .const import (
    CMD_TYPE_FIXED,
    CMD_TYPE_PROGRAM_SELECT,
    CMD_TYPE_USER_OPTION,
    DOOR_STATE_CLOSED_OR_LOCKED,
    DOOR_STATE_LOCKED,
    FIXED_CMD_CANCEL,
    FIXED_CMD_PAUSE,
    FIXED_CMD_PLAY,
    FIXED_CMD_POWER_OFF,
    FIXED_CMD_STATUS_QUERY,
    FRAME_HEADER,
    HIL_OPTION_CHILD_LOCK,
    HIL_OPTION_DELAY,
    HIL_OPTION_SPIN,
    MachineState,
    PROGRAM_CODES_742,
    SPIN_SPEED_OPTIONS,
    STATE_LABELS,
    TEMPERATURE_OPTIONS,
)
from .exceptions import IFBProtocolError


def compute_checksums(data: bytes | list[int]) -> tuple[int, int]:
    """Calculate the two-byte IFB checksum using signed byte accumulation."""
    s = 0
    for b in data:
        signed_b = b if b < 128 else b - 256
        s += signed_b
    s = s & 0xFFFF
    chk1 = s & 0xFF
    if s < 249:
        chk2 = (s * 2) & 0xFF
    else:
        hex_str = f"{s:02x}"
        chk2 = int(hex_str[-2], 16)
    return chk1, chk2


def build_status_query() -> bytes:
    """Build the standard 12-byte status query packet."""
    return bytes([FRAME_HEADER, 0x0A, CMD_TYPE_FIXED, 0x00, 0x01, FIXED_CMD_STATUS_QUERY, 0x00, 0x00, 0x00, 0x00, 0x76, 0xEC])


def build_child_lock_command(enable: bool) -> bytes:
    """Build the 12-byte child lock enable/disable packet."""
    val = 1 if enable else 0
    pkt = [FRAME_HEADER, 0x0A, CMD_TYPE_USER_OPTION, 0x01, HIL_OPTION_CHILD_LOCK, val, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
    chk1, chk2 = compute_checksums(pkt[:-2])
    pkt[-2] = chk1
    pkt[-1] = chk2
    return bytes(pkt)


def build_fixed_command(cmd_code: int) -> bytes:
    """Build a 12-byte fixed machine control command (Play, Pause, Cancel, Power Off)."""
    pkt = [FRAME_HEADER, 0x0A, CMD_TYPE_FIXED, 0x00, 0x01, cmd_code, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
    chk1, chk2 = compute_checksums(pkt[:-2])
    pkt[-2] = chk1
    pkt[-1] = chk2
    return bytes(pkt)


def build_program_selection(program_code: int, spin_rpm: int = 1000, temp_c: int = 40) -> bytes:
    """Build the 21-byte program selection packet."""
    pkt = [
        FRAME_HEADER,
        0x13,
        CMD_TYPE_PROGRAM_SELECT,
        0x00,
        0x01,
        program_code & 0xFF,
        0x00,
        (spin_rpm >> 8) & 0xFF,
        spin_rpm & 0xFF,
        temp_c & 0xFF,
        0x00,
        0x00,
        0x00,
        0x0A,
        0x01,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
    ]
    chk1, chk2 = compute_checksums(pkt[:-2])
    pkt[-2] = chk1
    pkt[-1] = chk2
    return bytes(pkt)


def build_user_option_command(hil_id: int, option_value: int) -> bytes:
    """Build a 9-byte user option selection packet (Spin, Temp, Extra Rinse, Soak, Delay)."""
    pkt = [
        FRAME_HEADER,
        0x07,
        CMD_TYPE_USER_OPTION,
        0x01,
        hil_id & 0xFF,
        0x00,
        0x00,
        0x00,
        0x00,
    ]
    if hil_id in (HIL_OPTION_SPIN, HIL_OPTION_DELAY):
        pkt[6] = option_value & 0xFF
    else:
        pkt[5] = option_value & 0xFF
    chk1, chk2 = compute_checksums(pkt[:-2])
    pkt[-2] = chk1
    pkt[-1] = chk2
    return bytes(pkt)


@dataclass
class WasherState:
    """Structured representation of decoded washing machine telemetry."""

    program_code: int
    program_name: str
    remaining_minutes: int
    state_code: int
    state_name: str
    door_locked: bool
    child_lock: bool
    spin_speed_code: int
    spin_speed_name: str
    temperature_code: int
    temperature_name: str
    motor_rpm: int
    water_temperature_c: int
    raw_hex: str

    @property
    def is_running(self) -> bool:
        """Return True if a cycle is actively running."""
        return self.state_code in (
            MachineState.STARTING,
            MachineState.PRE_WASH,
            MachineState.MAIN_WASH,
            MachineState.EXTRA_RINSE_1,
            MachineState.EXTRA_RINSE_2,
            MachineState.EXTRA_RINSE_3,
            MachineState.FIRST_RINSE,
            MachineState.SECOND_RINSE,
            MachineState.FINAL_RINSE,
            MachineState.FINAL_SPIN,
            MachineState.ANTI_CREASE,
            MachineState.SOAK,
            MachineState.RINSE_HOLD,
            MachineState.HEATING,
            MachineState.DRAINING,
            MachineState.INTERMEDIATE_SPIN,
            MachineState.COOLING,
            MachineState.HOT_RINSE_START,
            MachineState.STEAM,
            MachineState.DRY,
        )

    @property
    def is_standby(self) -> bool:
        """Return True if the machine is idle in Standby."""
        return self.state_code == MachineState.STANDBY

    @property
    def is_paused(self) -> bool:
        """Return True if the current cycle is paused."""
        return self.state_code == MachineState.PAUSED

    @property
    def is_complete(self) -> bool:
        """Return True if the wash cycle has completed."""
        return self.state_code == MachineState.COMPLETE


def parse_status_frame(data: bytes) -> WasherState:
    """Parse and validate a raw binary response frame into a WasherState instance."""
    if len(data) < 36:
        raise IFBProtocolError(f"Frame length {len(data)} is too short for status parsing")

    if data[0] != FRAME_HEADER:
        raise IFBProtocolError(f"Invalid frame header: 0x{data[0]:02X}")

    # Validate checksum
    expected_c1, expected_c2 = compute_checksums(data[:-2])
    if data[-2] != expected_c1 or data[-1] != expected_c2:
        raise IFBProtocolError(
            f"Checksum mismatch: expected ({expected_c1}, {expected_c2}), got ({data[-2]}, {data[-1]})"
        )

    prog_id = data[6]
    prog_name = PROGRAM_CODES_742.get(prog_id, f"Program {prog_id}")

    spin_opt = data[8]
    spin_name = SPIN_SPEED_OPTIONS.get(spin_opt, f"{spin_opt}")

    temp_opt = data[10]
    temp_name = TEMPERATURE_OPTIONS.get(temp_opt, f"{temp_opt}")

    child_lock_active = bool(data[15])
    rem_h = data[17]
    rem_m = data[18]
    rem_total = (rem_h * 60) + rem_m

    motor_rpm = (data[19] << 8) | data[20]
    water_temp = data[21]

    state_code = data[30]
    state_name = STATE_LABELS.get(state_code, f"State {state_code}")

    door_raw = data[31]
    door_locked = door_raw in (DOOR_STATE_CLOSED_OR_LOCKED, DOOR_STATE_LOCKED)

    return WasherState(
        program_code=prog_id,
        program_name=prog_name,
        remaining_minutes=rem_total,
        state_code=state_code,
        state_name=state_name,
        door_locked=door_locked,
        child_lock=child_lock_active,
        spin_speed_code=spin_opt,
        spin_speed_name=spin_name,
        temperature_code=temp_opt,
        temperature_name=temp_name,
        motor_rpm=motor_rpm,
        water_temperature_c=water_temp,
        raw_hex=data.hex(),
    )
