"""Unit tests for IFB Washer protocol encoding, decoding, and checksum verification."""

import pytest
from ifb_washer_local.const import (
    FIXED_CMD_CANCEL,
    FIXED_CMD_PAUSE,
    FIXED_CMD_PLAY,
    HIL_OPTION_CHILD_LOCK,
    HIL_OPTION_SPIN,
    HIL_OPTION_TEMP,
    MachineState,
)
from ifb_washer_local.protocol import (
    build_child_lock_command,
    build_fixed_command,
    build_program_selection,
    build_status_query,
    build_user_option_command,
    compute_checksums,
    parse_status_frame,
)


def test_status_query_checksum():
    """Verify standard status query packet checksums."""
    pkt = build_status_query()
    assert len(pkt) == 12
    assert pkt[0] == 0x63
    c1, c2 = compute_checksums(pkt[:-2])
    assert pkt[-2] == c1 == 0x76
    assert pkt[-1] == c2 == 0xEC


def test_child_lock_commands():
    """Verify child lock enable and disable packet serialization and checksums."""
    on_pkt = build_child_lock_command(True)
    assert len(on_pkt) == 12
    assert on_pkt[4] == HIL_OPTION_CHILD_LOCK
    assert on_pkt[5] == 0x01
    assert on_pkt[-2] == 0x7C
    assert on_pkt[-1] == 0xF8

    off_pkt = build_child_lock_command(False)
    assert len(off_pkt) == 12
    assert off_pkt[4] == HIL_OPTION_CHILD_LOCK
    assert off_pkt[5] == 0x00
    assert off_pkt[-2] == 0x7B
    assert off_pkt[-1] == 0xF6


def test_parse_real_mix_daily_telemetry():
    """Verify decoding of a live capture for Mix / Daily on 742 hardware."""
    raw = bytes.fromhex("6324810001070d01060002220000000000010c00002200000000000000000101000000017af4")
    state = parse_status_frame(raw)

    assert state.program_code == 13
    assert state.program_name == "Mix / Daily"
    assert state.remaining_minutes == 72  # 1h 12m
    assert state.temperature_code == 2
    assert state.temperature_name == "Cold"
    assert state.spin_speed_code == 6
    assert state.spin_speed_name == "1000 RPM"
    assert state.state_code == MachineState.STANDBY
    assert state.is_standby is True
    assert state.is_running is False
    assert state.door_locked is False
    assert state.child_lock is False


def test_parse_real_cotton_telemetry():
    """Verify decoding of a live capture for Cotton on 742 hardware."""
    raw = bytes.fromhex("6324810001070c01080004220000000000022b00002200000000000000000101000000019d3a")
    state = parse_status_frame(raw)

    assert state.program_code == 12
    assert state.program_name == "Cotton"
    assert state.remaining_minutes == 163  # 2h 43m
    assert state.temperature_code == 4
    assert state.temperature_name == "40°C"
    assert state.spin_speed_code == 8
    assert state.state_code == MachineState.STANDBY
    assert state.is_standby is True


def test_program_selection_packet():
    """Verify program selection packet building."""
    pkt = build_program_selection(13, spin_rpm=1000, temp_c=40)
    assert len(pkt) == 21
    assert pkt[0] == 0x63
    assert pkt[2] == 0x03
    assert pkt[5] == 13
    c1, c2 = compute_checksums(pkt[:-2])
    assert pkt[-2] == c1
    assert pkt[-1] == c2


def test_verified_15_programs_mapping():
    """Verify the 15 hardware-verified dial program codes."""
    from ifb_washer_local.const import (
        PROGRAM_CODES_742,
        PROGRAM_CODES_WASHER_DRYER,
    )

    assert PROGRAM_CODES_WASHER_DRYER == PROGRAM_CODES_742
    assert len(PROGRAM_CODES_WASHER_DRYER) == 15
    assert PROGRAM_CODES_WASHER_DRYER[1] == "Wash + Dry 2Hr"
    assert PROGRAM_CODES_WASHER_DRYER[2] == "Wash + Dry 4Hr"
    assert PROGRAM_CODES_WASHER_DRYER[12] == "Cotton"
    assert PROGRAM_CODES_WASHER_DRYER[13] == "Mix / Daily"
    assert PROGRAM_CODES_WASHER_DRYER[14] == "Express 15'"
    assert PROGRAM_CODES_WASHER_DRYER[15] == "Tub Clean"


def test_family_program_matrices():
    """Verify family matrices are populated correctly."""
    from ifb_washer_local.const import (
        FAMILY_PROGRAM_MATRICES,
        PROGRAM_CODES_FRONT_LOAD,
        PROGRAM_CODES_TOP_LOAD,
        ApplianceFamily,
    )

    assert ApplianceFamily.WASHER_DRYER in FAMILY_PROGRAM_MATRICES
    assert ApplianceFamily.FRONT_LOAD in FAMILY_PROGRAM_MATRICES
    assert ApplianceFamily.TOP_LOAD_SMART in FAMILY_PROGRAM_MATRICES

    assert PROGRAM_CODES_FRONT_LOAD[1] == "Mix / Daily"
    assert PROGRAM_CODES_FRONT_LOAD[20] == "Spin Dry / Rinse"
    assert PROGRAM_CODES_TOP_LOAD[1] == "Mix / Daily"
    assert PROGRAM_CODES_TOP_LOAD[10] == "Tub Clean"


def test_signature_auto_detection():
    """Verify reverse-engineering of cycle names via telemetry signatures."""
    from ifb_washer_local.protocol import detect_program_from_telemetry

    # Express 15'
    assert detect_program_from_telemetry(duration_min=15, temp_c=0, spin_rpm=800) == "Express 15'"
    # Cotton (with +/- 2 min variance)
    assert detect_program_from_telemetry(duration_min=165, temp_c=60, spin_rpm=1400) == "Cotton"
    # Wash + Dry 2Hr (dry flag enabled)
    assert detect_program_from_telemetry(duration_min=120, temp_c=40, spin_rpm=1000, is_dry_enabled=True) == "Wash + Dry 2Hr"
    # Wash + Dry 2Hr should not match without dry flag
    assert detect_program_from_telemetry(duration_min=120, temp_c=40, spin_rpm=1000, is_dry_enabled=False) is None


def test_error_fault_parsing():
    """Verify decoding of problem conditions in telemetry frame."""
    # Base packet with Tap error injected at alarm2 register (byte 27, bit 1: 0x02)
    raw = bytearray.fromhex("6324810001070d01060002220000000000010c00002200000000000000000101000000017af4")
    raw[27] = 2  # tAP error in alarm2 register
    c1, c2 = compute_checksums(raw[:-2])
    raw[-2] = c1
    raw[-1] = c2

    state = parse_status_frame(bytes(raw))
    assert state.has_problem is True
    assert state.error_code == "tAP"
    assert "Water" in state.error_description


def test_unbalance_alarm_parsing():
    """Verify unbalance error from alarm2 bit 7 (0x80 = 128)."""
    raw = bytearray.fromhex("6324810001070d01060002220000000000010c00002200000000000000000101000000017af4")
    raw[27] = 128  # alarm2 bit 7: unbalance
    c1, c2 = compute_checksums(raw[:-2])
    raw[-2] = c1
    raw[-1] = c2

    state = parse_status_frame(bytes(raw))
    assert state.has_problem is True
    assert state.error_code == "unb"
    assert "Unbalance" in state.error_description


def test_parse_status_frame_custom_map():
    """Verify parsing with a custom program dictionary."""
    custom_map = {13: "Custom Cycle"}
    raw = bytes.fromhex("6324810001070d01060002220000000000010c00002200000000000000000101000000017af4")
    state = parse_status_frame(raw, program_map=custom_map)
    assert state.program_name == "Custom Cycle"


def test_checksum_large_sum_power_steam():
    """Verify checksum calculation for frames where accumulation >= 249 (e.g. Power Steam s=252)."""
    # Create dummy data whose signed sum equals 252
    # 252 can be represented by two 126 bytes
    dummy = bytes([126, 126])
    c1, c2 = compute_checksums(dummy)
    assert c1 == 252
    assert c2 == 248  # (252 * 2) & 0xFF == 248 (previously miscalculated as 15)


def test_door_states_unlocked_and_locked():
    """Verify byte 35 door state parsing (1=unlocked, 2=locked)."""
    # Base packet with byte 35 = 1 (unlocked)
    raw = bytearray.fromhex("6324810001070d01060002220000000000010c00002200000000000000000101000000017af4")
    raw[35] = 1
    c1, c2 = compute_checksums(raw[:-2])
    raw[-2], raw[-1] = c1, c2
    state = parse_status_frame(bytes(raw))
    assert state.door_locked is False
    assert state.door_state_code == 1

    # Byte 35 = 2 (locked)
    raw[35] = 2
    c1, c2 = compute_checksums(raw[:-2])
    raw[-2], raw[-1] = c1, c2
    state = parse_status_frame(bytes(raw))
    assert state.door_locked is True
    assert state.door_state_code == 2


def test_tub_temperature_and_progress_calculation():
    """Verify tub temperature (byte 21) and progress calculation from program time (bytes 32-33)."""
    raw = bytearray.fromhex("6324810001070d01060007200000000000001a0032210000002600000000080201040002efde")
    # In this packet:
    # byte 10 = 0x07 (20°C)
    # byte 17-18 = 0, 26 (rem=26m)
    # byte 21 = 0x21 (tub temp 33°C)
    # byte 30 = 0x08 (First Rinse)
    # byte 32-33 = 1, 4 (total=64m)
    # byte 35 = 2 (door locked)
    c1, c2 = compute_checksums(raw[:-2])
    raw[-2], raw[-1] = c1, c2
    state = parse_status_frame(bytes(raw))

    assert state.temperature_name == "20°C"
    assert state.tub_temperature_c == 33
    assert state.water_temperature_c == 33  # Backwards compatibility alias
    assert state.total_program_minutes == 64
    assert state.remaining_minutes == 26
    # (64 - 26) * 100 / 64 = 3800 / 64 = 59.4%
    assert state.cycle_progress == 59.4
    assert state.door_locked is True
    assert state.has_problem is False
    assert state.delay_start_minutes == 0
    assert state.is_delay_start is False


def test_delay_start_parsing():
    """Verify parsing of delay start registers (bytes 12-13) and state code."""
    raw = bytearray.fromhex("6324810001070d01060002220000000000010c00002200000000000000000101000000017af4")
    # Set delay: 2 hours (byte 12 = 2), 30 minutes (byte 13 = 30 = 0x1E)
    raw[12] = 2
    raw[13] = 30
    raw[30] = 20  # MachineState.DELAY_START
    c1, c2 = compute_checksums(raw[:-2])
    raw[-2], raw[-1] = c1, c2

    state = parse_status_frame(bytes(raw))
    assert state.delay_start_minutes == 150  # 2*60 + 30
    assert state.is_delay_start is True
    assert state.state_name == "Delay Start"

