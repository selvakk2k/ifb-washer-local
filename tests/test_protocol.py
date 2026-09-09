"""Unit tests for IFB Washer protocol encoding, decoding, and checksum verification."""

import pytest
from ifb_washer_local.const import (
    FIXED_CMD_CANCEL,
    FIXED_CMD_PAUSE,
    FIXED_CMD_PLAY,
    FIXED_CMD_POWER_ON,
    FIXED_CMD_POWER_OFF,
    HIL_OPTION_CHILD_LOCK,
    HIL_OPTION_DRY,
    HIL_OPTION_EXTRA_RINSE,
    HIL_OPTION_HOT_RINSE,
    HIL_OPTION_PRE_WASH,
    HIL_OPTION_RINSE_HOLD,
    HIL_OPTION_SOAK,
    HIL_OPTION_SPIN,
    HIL_OPTION_STEAM,
    HIL_OPTION_TEMP,
    HIL_OPTION_TIME_SAVER,
    HIL_OPTION_ECO,
    HIL_OPTION_AROMA,
    HIL_OPTION_ANTI_CREASE,
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


def test_power_on_off_fixed_commands():
    """Verify serialization of power on and power off fixed commands against official frames."""
    # Power ON: cmd 0x11 -> 63 0a 01 00 01 11 00 00 00 00 80 00
    on_pkt = build_fixed_command(FIXED_CMD_POWER_ON)
    assert on_pkt.hex() == "630a01000111000000008000"

    # Power OFF: cmd 0x12 -> 63 0a 01 00 01 12 00 00 00 00 81 02
    off_pkt = build_fixed_command(FIXED_CMD_POWER_OFF)
    assert off_pkt.hex() == "630a01000112000000008102"


def test_power_state_telemetry_parsing():
    """Verify decoding of powered on vs powered off status via byte 7 bit 6."""
    raw = bytearray.fromhex("6324810001070d01060002220000000000010c00002200000000000000000101000000017af4")
    # Byte 7 = 0x01 (0000 0001) -> bit 6 is 0 -> is_powered_on is True (Active / ON)
    c1, c2 = compute_checksums(raw[:-2])
    raw[-2], raw[-1] = c1, c2
    state_on = parse_status_frame(bytes(raw))
    assert state_on.is_powered_on is True

    # Byte 7 = 0x41 (0100 0001) -> bit 6 is 1 -> is_powered_on is False (Standby / OFF)
    raw[7] = 0x41
    c1, c2 = compute_checksums(raw[:-2])
    raw[-2], raw[-1] = c1, c2
    state_off = parse_status_frame(bytes(raw))
    assert state_off.is_powered_on is False


def test_extra_rinse_and_dry_mode_telemetry():
    """Verify parsing of extra rinse count (byte 9) and dry mode code (byte 28)."""
    raw = bytearray.fromhex("6324810001070d01060002220000000000010c00002200000000000000000101000000017af4")
    # Byte 9 = 2 (+2 Rinses), Byte 28 = 1 (Cupboard Dry)
    raw[9] = 2
    raw[28] = 1
    c1, c2 = compute_checksums(raw[:-2])
    raw[-2], raw[-1] = c1, c2

    state = parse_status_frame(bytes(raw))
    assert state.extra_rinse == 2
    assert state.extra_rinse_name == "+2 Rinses"
    assert state.dry_mode_code == 1
    assert state.dry_mode_name == "Cupboard Dry"


def test_modifier_options_telemetry():
    """Verify decoding of option2 (byte 11) and optionEnable1 (byte 29) bitmasks."""
    raw = bytearray.fromhex("6324810001070d01060002220000000000010c00002200000000000000000101000000017af4")
    # Byte 11 (option2): rinse_hold (bit 2 = 4), anti_crease (bit 3 = 8), aroma (bit 6 = 64) -> 4 + 8 + 64 = 76 (0x4C)
    raw[11] = 0x4C
    # Byte 29 (optionEnable1): prewash (bit 0 = 1), soak (bit 1 = 2), hot_rinse (bit 3 = 8), time_saver (bit 4 = 16), eco (bit 6 = 64) -> 91 (0x5B)
    raw[29] = 0x5B
    c1, c2 = compute_checksums(raw[:-2])
    raw[-2], raw[-1] = c1, c2

    state = parse_status_frame(bytes(raw))
    assert state.rinse_hold is True
    assert state.anti_crease is True
    assert state.aroma is True
    assert state.prewash is True
    assert state.soak is True
    assert state.hot_rinse is True
    assert state.time_saver is True
    assert state.eco is True


def test_build_feature_option_commands():
    """Verify packet encoding for new HIL option commands."""
    # Extra rinse = 2 -> 9-byte packet with pkt[4]=7, pkt[5]=2
    pkt_rinse = build_user_option_command(HIL_OPTION_EXTRA_RINSE, 2)
    assert len(pkt_rinse) == 9
    assert pkt_rinse[4] == HIL_OPTION_EXTRA_RINSE
    assert pkt_rinse[5] == 2
    c1, c2 = compute_checksums(pkt_rinse[:-2])
    assert pkt_rinse[-2] == c1
    assert pkt_rinse[-1] == c2

    # Dry mode = 1 -> pkt[4]=18, pkt[5]=1
    pkt_dry = build_user_option_command(HIL_OPTION_DRY, 1)
    assert len(pkt_dry) == 9
    assert pkt_dry[4] == HIL_OPTION_DRY
    assert pkt_dry[5] == 1
    c1, c2 = compute_checksums(pkt_dry[:-2])
    assert pkt_dry[-2] == c1
    assert pkt_dry[-1] == c2

    # Pre-wash enable = 1 -> pkt[4]=6, pkt[5]=1
    pkt_prewash = build_user_option_command(HIL_OPTION_PRE_WASH, 1)
    assert len(pkt_prewash) == 9
    assert pkt_prewash[4] == HIL_OPTION_PRE_WASH
    assert pkt_prewash[5] == 1
    c1, c2 = compute_checksums(pkt_prewash[:-2])
    assert pkt_prewash[-2] == c1
    assert pkt_prewash[-1] == c2

def test_program_capabilities_wash_guide_map():
    """Verify Wash Guide Map capabilities for various programs."""
    from ifb_washer_local.const import get_program_capabilities

    # Refresh (4): Tumble only, No Spin, Cold only, no dry
    refresh_caps = get_program_capabilities(4)
    assert refresh_caps.allowed_spins == ("No Spin",)
    assert refresh_caps.allowed_temps == ("Cold",)
    assert refresh_caps.supports_dry is False
    assert refresh_caps.supports_steam is True

    # CradleWash (6): Gentle wash, max 600 RPM, max 40°C, no dry
    cradle_caps = get_program_capabilities(6)
    assert cradle_caps.allowed_spins == ("No Spin", "400 RPM", "600 RPM")
    assert "95°C" not in cradle_caps.allowed_temps
    assert cradle_caps.supports_dry is False

    # Wash + Dry 2Hr (1): Supports dry
    wd_caps = get_program_capabilities(1)
    assert wd_caps.supports_dry is True
    assert wd_caps.supports_prewash is False

    # Cotton (12): Supports all temps and spins up to 1400 RPM
    cotton_caps = get_program_capabilities(12)
    assert "95°C" in cotton_caps.allowed_temps
    assert "1400 RPM" in cotton_caps.allowed_spins
    assert cotton_caps.supports_dry is False
