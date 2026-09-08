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
    assert state.door_locked is True
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
