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
    PROGRAM_CODES_WASHER_DRYER,
    SPIN_SPEED_OPTIONS,
    STATE_LABELS,
    TELEMETRY_SIGNATURES,
    TEMPERATURE_OPTIONS,
    ERROR_CODES,
    DRY_OPTIONS,
    EXTRA_RINSE_OPTIONS,
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
    chk2 = (s * 2) & 0xFF
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


def build_program_selection(
    program_code: int,
    spin_code: int = 6,
    temp_code: int = 4,
    child_lock: bool = False,
) -> bytes:
    """Build the 21-byte program selection packet with discrete hardware option codes."""
    pkt = [
        FRAME_HEADER,
        0x13,
        CMD_TYPE_PROGRAM_SELECT,
        0x00,
        0x00,
        program_code & 0xFF,
        0x00,
        spin_code & 0xFF,
        0x00,
        temp_code & 0xFF,
        0x00,
        0x00,
        0x00,
        0x00,
        1 if child_lock else 0,
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
    """Build a 9-byte user option selection packet (Extra Rinse, Soak, Delay, Dry, Modifiers)."""
    pkt = [
        FRAME_HEADER,
        0x07,
        CMD_TYPE_USER_OPTION,
        0x01,
        hil_id & 0xFF,
        option_value & 0xFF,
        0x00,
        0x00,
        0x00,
    ]
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
    tub_temperature_c: int
    raw_hex: str
    door_state_code: int = 1
    total_program_minutes: int = 0
    cycle_progress: float = 0.0
    tub_clean_required: bool = False
    delay_start_minutes: int = 0
    is_powered_on: bool = True
    error_code: str = ""
    error_description: str = ""
    extra_rinse: int = 0
    extra_rinse_name: str = "0 (None)"
    dry_mode_code: int = 0
    dry_mode_name: str = "Off"
    prewash: bool = False
    soak: bool = False
    rinse_hold: bool = False
    time_saver: bool = False
    hot_rinse: bool = False
    eco: bool = False
    steam: bool = False
    aroma: bool = False
    anti_crease: bool = False
    rapid_wash: bool = False
    warm_soak: bool = False

    @property
    def is_delay_start(self) -> bool:
        """Return True if the machine is waiting in Delay Start countdown."""
        return self.state_code == MachineState.DELAY_START or (
            self.delay_start_minutes > 0 and self.state_code == MachineState.STANDBY
        )

    @property
    def water_temperature_c(self) -> int:
        """Alias for tub_temperature_c for backwards compatibility."""
        return self.tub_temperature_c

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

    @property
    def has_problem(self) -> bool:
        """Return True if an error or fault condition is detected."""
        return bool(self.error_code)


def detect_program_from_telemetry(
    duration_min: int,
    temp_c: int = 0,
    spin_rpm: int = 0,
    is_dry_enabled: bool = False,
    tolerance_minutes: int = 5,
) -> str | None:
    """Reverse-engineer program identity from running telemetry parameters."""
    for sig in TELEMETRY_SIGNATURES:
        if abs(sig.duration_min - duration_min) <= tolerance_minutes:
            if sig.is_dry_enabled != is_dry_enabled:
                continue
            if sig.temp_c != 0 and temp_c != 0 and sig.temp_c != temp_c:
                continue
            if sig.spin_rpm != 0 and spin_rpm != 0 and sig.spin_rpm != spin_rpm:
                continue
            return sig.name
    return None



def decode_alarms(
    alarm1: int = 0,
    alarm2: int = 0,
    alarm3: int = 0,
    alarm4: int = 0,
) -> tuple[str, str]:
    """Decode alarm registers into error code and description matching the official IFB app.

    Bitmask definitions from WasherOptionActivity.java and l1.java:
    - alarm1 (byte 26): door (bit 0/7), triac (bit 1), motor (bit 3), overflow (bit 4),
      overheat (bit 5), pressure switch (bit 6).
    - alarm2 (byte 27): tap/no water (bit 0/1), heating (bit 2), temp sensor (bit 3),
      drain pump (bit 4), low voltage (bit 5), high voltage (bit 6), unbalance (bit 7).
    - alarm3 (byte 24): blocked rotor (bit 0), dryer sensor (bit 1), dryer fan (bit 2),
      motor overcurrent (bit 3), ipm overheat (bit 4), power board comms (bit 5),
      hot (bit 6), dryer heater (bit 7).
    - alarm4 (byte 41): drying sensor fault (bit 0).
    """
    # alarm1 (v.a.a in official app)
    if alarm1 != 0:
        if alarm1 & 1 or alarm1 & 128:
            return ERROR_CODES.get(1, ("door", "Door Error"))
        if alarm1 & 2:
            return ERROR_CODES.get(7, ("tri", "Triac Short"))
        if alarm1 & 8:
            return ERROR_CODES.get(5, ("mot", "Motor Failure"))
        if alarm1 & 16:
            return ERROR_CODES.get(4, ("ofl", "Water Overflow"))
        if alarm1 & 32:
            return ERROR_CODES.get(3, ("oht", "Over Heat"))
        if alarm1 & 64:
            return ERROR_CODES.get(2, ("prs", "Pressure Switch Failure"))
        if alarm1 in ERROR_CODES:
            return ERROR_CODES[alarm1]
        return ERROR_CODES.get(24, ("unk", "Unknown Error"))

    # alarm2 (v.b.a in official app)
    if alarm2 != 0:
        if alarm2 & 1 or alarm2 & 2:
            return ERROR_CODES.get(14, ("tAP", "No Water / Low Water Pressure"))
        if alarm2 & 4:
            return ERROR_CODES.get(13, ("htr", "Heating Error"))
        if alarm2 & 8:
            return ERROR_CODES.get(12, ("tsn", "Temperature Sensor Error"))
        if alarm2 & 16:
            return ERROR_CODES.get(11, ("drn", "Drain Pump Failure"))
        if alarm2 & 32:
            return ERROR_CODES.get(10, ("lvt", "Low Voltage"))
        if alarm2 & 64:
            return ERROR_CODES.get(9, ("hvt", "High Voltage"))
        if alarm2 & 128:
            return ERROR_CODES.get(8, ("unb", "Unbalance Error"))
        if alarm2 in ERROR_CODES:
            return ERROR_CODES[alarm2]
        return ERROR_CODES.get(24, ("unk", "Unknown Error"))

    # alarm3 (v.c.a in official app)
    if alarm3 != 0:
        if alarm3 & 1:
            return ERROR_CODES.get(23, ("bkr", "Blocked Rotor"))
        if alarm3 & 2:
            return ERROR_CODES.get(22, ("dsn", "Clothes Not Drying - Dryer Sensor Fault"))
        if alarm3 & 4:
            return ERROR_CODES.get(21, ("dfn", "Dryer Fan Fault"))
        if alarm3 & 8:
            return ERROR_CODES.get(20, ("moc", "Motor Over Current"))
        if alarm3 & 16:
            return ERROR_CODES.get(19, ("ipm", "IPM Overheat"))
        if alarm3 & 32:
            return ERROR_CODES.get(18, ("pwr", "Power Board Communication Error"))
        if alarm3 & 64:
            return ERROR_CODES.get(6, ("hot", "Hot (High Drum Temp)"))
        if alarm3 & 128:
            return ERROR_CODES.get(16, ("dht", "Clothes Not Drying - Dryer Heater Fault"))
        if alarm3 in ERROR_CODES:
            return ERROR_CODES[alarm3]
        return ERROR_CODES.get(24, ("unk", "Unknown Error"))

    # alarm4 (v.d.a in official app)
    if alarm4 != 0:
        if alarm4 & 1:
            return ERROR_CODES.get(30, ("dsf", "Clothes Not Drying - Drying Sensor Fault"))
        if alarm4 in ERROR_CODES:
            return ERROR_CODES[alarm4]
        return ERROR_CODES.get(24, ("unk", "Unknown Error"))

    return ("", "No Error")


def parse_status_frame(
    data: bytes,
    program_map: dict[int, str] | None = None,
) -> WasherState:
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

    active_program_map = program_map if program_map is not None else PROGRAM_CODES_WASHER_DRYER
    prog_id = data[6]
    prog_name = active_program_map.get(prog_id, f"Program {prog_id}")

    spin_opt = data[8]
    spin_name = SPIN_SPEED_OPTIONS.get(spin_opt, f"{spin_opt}")

    temp_opt = data[10]
    temp_name = TEMPERATURE_OPTIONS.get(temp_opt, f"{temp_opt}")

    delay_h = data[12]
    delay_m = data[13]
    delay_start_minutes = (delay_h * 60) + delay_m

    child_lock_active = bool(data[15])
    rem_h = data[17]
    rem_m = data[18]
    rem_total = (rem_h * 60) + rem_m

    motor_rpm = (data[19] << 8) | data[20]
    tub_temp = data[21]

    state_code = data[30]
    state_name = STATE_LABELS.get(state_code, f"State {state_code}")

    door_raw = data[35]
    door_locked = (door_raw == DOOR_STATE_LOCKED)

    total_prog_h = data[32]
    total_prog_m = data[33]
    total_program_minutes = (total_prog_h * 60) + total_prog_m
    if total_program_minutes == 0 and rem_total > 0:
        total_program_minutes = rem_total

    if total_program_minutes > 0 and total_program_minutes >= rem_total:
        cycle_progress = round(((total_program_minutes - rem_total) * 100.0) / total_program_minutes, 1)
    elif rem_total == 0 and state_code == MachineState.COMPLETE:
        cycle_progress = 100.0
    else:
        cycle_progress = 0.0

    tub_clean_required = bool(state_code == MachineState.COMPLETE and ((data[7] >> 7) & 1) == 1)
    is_powered_on = not bool((data[7] >> 6) & 1)

    # Fault / Problem Detection from dedicated alarm registers:
    # data[24] = alarm3, data[26] = alarm1, data[27] = alarm2, data[41] = alarm4
    # (Note: data[25] is drum unbalance measurement, NOT an error flag. Unbalance error is alarm2 bit 7).
    a1 = data[26]
    a2 = data[27]
    a3 = data[24]
    a4 = data[41] if len(data) > 41 else 0
    error_code, error_desc = decode_alarms(a1, a2, a3, a4)

    # If actively running but door is unlatched, register door fault
    if not error_code and not door_locked:
        if state_code in (
            MachineState.STARTING,
            MachineState.PRE_WASH,
            MachineState.MAIN_WASH,
            MachineState.FINAL_SPIN,
            MachineState.INTERMEDIATE_SPIN,
        ):
            error_code, error_desc = ERROR_CODES[1]

    # Extra Rinse count (byte 9)
    extra_rinse_count = data[9] if len(data) > 9 else 0
    extra_rinse_name = EXTRA_RINSE_OPTIONS.get(extra_rinse_count, f"{extra_rinse_count} Rinses")

    # Options register 2 (byte 11): bit 0=soil age, bit 1=favorite, bit 2=rinse hold,
    # bit 3=anti-crease, bit 6=aroma, bit 9=steam (or machine in Steam state)
    opt2 = data[11] if len(data) > 11 else 0
    rinse_hold = bool((opt2 >> 2) & 1)
    anti_crease = bool((opt2 >> 3) & 1)
    aroma = bool((opt2 >> 6) & 1)
    steam = bool(((opt2 >> 9) & 1) or state_code == MachineState.STEAM)

    # Dry Mode Option (byte 28)
    dry_code = data[28] if len(data) > 28 else 0
    dry_name = DRY_OPTIONS.get(dry_code, f"Mode {dry_code}")

    # Enabled Options 1 (byte 29): bit 0=pre-wash, bit 1=soak, bit 2=warm soak,
    # bit 3=hot rinse, bit 4=time saver, bit 6=eco, bit 7=rapid wash
    opt_enable1 = data[29] if len(data) > 29 else 0
    prewash = bool((opt_enable1 >> 0) & 1)
    soak = bool((opt_enable1 >> 1) & 1)
    warm_soak = bool((opt_enable1 >> 2) & 1)
    hot_rinse = bool((opt_enable1 >> 3) & 1)
    time_saver = bool((opt_enable1 >> 4) & 1)
    eco = bool((opt_enable1 >> 6) & 1)
    rapid_wash = bool((opt_enable1 >> 7) & 1)

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
        tub_temperature_c=tub_temp,
        raw_hex=data.hex(),
        door_state_code=door_raw,
        total_program_minutes=total_program_minutes,
        cycle_progress=cycle_progress,
        tub_clean_required=tub_clean_required,
        delay_start_minutes=delay_start_minutes,
        is_powered_on=is_powered_on,
        error_code=error_code,
        error_description=error_desc,
        extra_rinse=extra_rinse_count,
        extra_rinse_name=extra_rinse_name,
        dry_mode_code=dry_code,
        dry_mode_name=dry_name,
        prewash=prewash,
        soak=soak,
        rinse_hold=rinse_hold,
        time_saver=time_saver,
        hot_rinse=hot_rinse,
        eco=eco,
        steam=steam,
        aroma=aroma,
        anti_crease=anti_crease,
        rapid_wash=rapid_wash,
        warm_soak=warm_soak,
    )

