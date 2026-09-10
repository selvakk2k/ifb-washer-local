import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ifb_washer_local.coordinator import IFBWasherCoordinator
from ifb_washer_local import (
    ApplianceFamily,
    IFBWasherClient,
    ProgramCapabilities,
    WasherState,
    calibrate_appliance_detailed,
    calibrate_appliance_quick,
    calibrate_appliance_simple,
    deserialize_capabilities_map,
    probe_single_program,
    serialize_capabilities_map,
)
from ifb_washer_local.const import (
    PROGRAM_CAPABILITIES_WASHER_DRYER,
    PROGRAM_CODES_WASHER_DRYER,
)


@pytest.fixture
def mock_hass():
    """Create a mocked HomeAssistant core instance."""
    hass = MagicMock()
    hass.data = {}
    hass.config_entries = MagicMock()
    hass.config_entries.async_update_entry = MagicMock()
    hass.async_add_executor_job = AsyncMock(return_value=None)
    return hass



def _build_mock_washer_state(
    program_code: int = 13,
    spin_code: int = 4,
    temp_code: int = 4,
    rinse_hold: bool = False,
    extra_rinse: int = 0,
    dry_mode: int = 0,
) -> WasherState:
    """Build a mock WasherState with raw hex byte payload."""
    raw = bytearray(36)
    raw[0] = 0x01
    raw[6] = program_code
    raw[8] = spin_code
    raw[9] = extra_rinse
    raw[10] = temp_code
    raw[11] = 0x24 if rinse_hold else 0x20
    raw[28] = dry_mode

    st = WasherState(
        program_code=program_code,
        program_name="Mix / Daily",
        remaining_minutes=45,
        state_code=1,
        state_name="Standby",
        door_locked=False,
        child_lock=False,
        spin_speed_code=spin_code,
        spin_speed_name="800 RPM",
        temperature_code=temp_code,
        temperature_name="40°C",
        motor_rpm=0,
        tub_temperature_c=30,
        rinse_hold=rinse_hold,
        extra_rinse=extra_rinse,
        dry_mode_code=dry_mode,
        dry_mode_name="No Dry",
        is_powered_on=True,
        raw_hex=raw.hex(),
    )
    return st



@pytest.mark.asyncio
async def test_serialize_deserialize_capabilities_map():
    """Test serialization and deserialization roundtrip of capabilities with metadata envelope."""
    original = {
        13: ProgramCapabilities(
            allowed_temps=("Cold", "30°C", "40°C"),
            allowed_spins=("No Spin", "600 RPM", "800 RPM", "1000 RPM"),
            supports_dry=False,
            allowed_dry_modes=("No Dry",),
            supports_rinse_hold=True,
        )
    }

    serialized = serialize_capabilities_map(original, mode="simple", model="Executive Plus ZXS")
    assert serialized["schema_version"] == 1
    assert serialized["calibration_mode"] == "simple"
    assert serialized["model"] == "Executive Plus ZXS"
    assert "capabilities" in serialized
    assert "13" in serialized["capabilities"]
    assert serialized["capabilities"]["13"]["allowed_spins"] == ["No Spin", "600 RPM", "800 RPM", "1000 RPM"]

    # Test deserialization from envelope
    deserialized = deserialize_capabilities_map(serialized)
    assert 13 in deserialized
    assert deserialized[13].allowed_spins == ("No Spin", "600 RPM", "800 RPM", "1000 RPM")
    assert deserialized[13].allowed_temps == ("Cold", "30°C", "40°C")

    # Test backwards compatibility with legacy raw dictionary format
    legacy_dict = {
        "13": original[13].to_dict()
    }
    legacy_deserialized = deserialize_capabilities_map(legacy_dict)
    assert 13 in legacy_deserialized
    assert legacy_deserialized[13].allowed_spins == ("No Spin", "600 RPM", "800 RPM", "1000 RPM")


@pytest.mark.asyncio
async def test_probe_single_program_detects_spin_and_temp():
    """Test single program probe correctly detects supported speeds and excludes rinse hold overflow."""
    client = MagicMock(spec=IFBWasherClient)
    client.select_program = AsyncMock()
    client._send_raw_command = AsyncMock()

    # When spin code is 0, 1, 2, 4, 6: accept
    # When spin code is 7 or 8: machine responds with rinse_hold=True or reverted
    def fake_get_state():
        # Last sent raw command determines mock response
        last_pkt = client._send_raw_command.call_args[0][0] if client._send_raw_command.call_args else b""
        if len(last_pkt) >= 8 and last_pkt[4] == 5:  # HIL_OPTION_SPIN
            sent_spin = last_pkt[6]
            if sent_spin in (7, 8):  # 1200 / 1400 on Mix/Daily triggers Rinse Hold
                return _build_mock_washer_state(spin_code=sent_spin, rinse_hold=True)
            return _build_mock_washer_state(spin_code=sent_spin, rinse_hold=False)
        elif len(last_pkt) >= 8 and last_pkt[4] == 4:  # HIL_OPTION_TEMP
            sent_temp = last_pkt[5]
            if sent_temp in (5, 6):  # 60°C / 95°C not allowed on synthetic program
                return _build_mock_washer_state(temp_code=2)
            return _build_mock_washer_state(temp_code=sent_temp)
        return _build_mock_washer_state()


    client.get_state = AsyncMock(side_effect=fake_get_state)

    caps = await probe_single_program(
        client,
        program_code=13,
        base_caps=PROGRAM_CAPABILITIES_WASHER_DRYER[13],
        is_washer_dryer=True,
        delay_between_cmds=0.001,
    )

    # 1200 RPM and 1400 RPM should NOT be in allowed spins because they triggered rinse hold
    assert "1200 RPM" not in caps.allowed_spins
    assert "1400 RPM" not in caps.allowed_spins
    assert "1000 RPM" in caps.allowed_spins
    assert "800 RPM" in caps.allowed_spins
    assert "600 RPM" in caps.allowed_spins
    assert "No Spin" in caps.allowed_spins


@pytest.mark.asyncio
async def test_calibrate_appliance_quick():
    """Test quick calibration iterates over core programs."""
    client = MagicMock(spec=IFBWasherClient)
    client.select_program = AsyncMock()
    client._send_raw_command = AsyncMock()
    client.get_state = AsyncMock(return_value=_build_mock_washer_state())

    prog_map = {1: "Cotton", 13: "Mix / Daily", 15: "Wash + Dry 60"}
    calibrated = await calibrate_appliance_quick(
        client,
        program_map=prog_map,
        base_caps_map=PROGRAM_CAPABILITIES_WASHER_DRYER,
        is_washer_dryer=True,
        delay_between_cmds=0.001,
    )

    assert 1 in calibrated
    assert 13 in calibrated
    assert 15 in calibrated


@pytest.mark.asyncio
async def test_calibrate_appliance_simple():
    """Test simple calibration iterates over all mapped programs within constraints."""
    client = MagicMock(spec=IFBWasherClient)
    client.select_program = AsyncMock()
    client._send_raw_command = AsyncMock()
    client.get_state = AsyncMock(return_value=_build_mock_washer_state())

    prog_map = {1: "Cotton", 13: "Mix / Daily", 14: "CradleWash®", 15: "Wash + Dry 60"}
    calibrated = await calibrate_appliance_simple(
        client,
        program_map=prog_map,
        base_caps_map=PROGRAM_CAPABILITIES_WASHER_DRYER,
        is_washer_dryer=True,
        delay_between_cmds=0.001,
    )

    assert 1 in calibrated
    assert 13 in calibrated
    assert 14 in calibrated
    assert 15 in calibrated


@pytest.mark.asyncio
async def test_coordinator_async_calibrate(mock_hass):
    """Test coordinator async_calibrate runs and persists data."""
    client = MagicMock(spec=IFBWasherClient)
    client.host = "192.168.0.100"
    client.get_state = AsyncMock(return_value=_build_mock_washer_state())
    client.select_program = AsyncMock()
    client._send_raw_command = AsyncMock()

    mock_entry = MagicMock()
    mock_entry.data = {}
    mock_entry.options = {}

    coord = IFBWasherCoordinator(mock_hass, client, entry=mock_entry)
    coord.data = _build_mock_washer_state()
    coord.async_request_refresh = AsyncMock()

    with patch(
        "custom_components.ifb_washer_local.coordinator.calibrate_appliance_quick",
        new_callable=AsyncMock,
        return_value={13: PROGRAM_CAPABILITIES_WASHER_DRYER[13]},
    ):
        result = await coord.async_calibrate("quick")
        assert 13 in result
        assert coord.calibrated_caps == result
        assert coord.get_program_capabilities(13) == PROGRAM_CAPABILITIES_WASHER_DRYER[13]
        mock_hass.config_entries.async_update_entry.assert_called_once()
        coord.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_profile_backup_and_metadata(tmp_path):
    """Test saving profile backup to file and extracting metadata."""
    from ifb_washer_local import extract_profile_metadata, save_profile_backup
    import json

    caps_map = {13: PROGRAM_CAPABILITIES_WASHER_DRYER[13]}
    filepath = save_profile_backup(
        str(tmp_path),
        caps_map,
        mode="simple",
        model="Executive Plus ZXS",
        family="washer_dryer",
    )
    assert os.path.exists(filepath)
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["schema_version"] == 1
    assert data["calibration_mode"] == "simple"
    assert data["model"] == "Executive Plus ZXS"
    assert "capabilities" in data
    assert "13" in data["capabilities"]

    meta = extract_profile_metadata(data)
    assert meta["calibration_mode"] == "simple"
    assert meta["model"] == "Executive Plus ZXS"


@pytest.mark.asyncio
async def test_coordinator_restore_and_clear_profile(mock_hass):
    """Test coordinator async_restore_profile and async_clear_profile."""
    client = MagicMock(spec=IFBWasherClient)
    client.host = "192.168.0.100"
    mock_entry = MagicMock()
    mock_entry.data = {}
    mock_entry.options = {}

    coord = IFBWasherCoordinator(mock_hass, client, entry=mock_entry)
    coord.async_request_refresh = AsyncMock()

    payload = serialize_capabilities_map(
        {13: PROGRAM_CAPABILITIES_WASHER_DRYER[13]},
        mode="simple",
        model="Test Model",
    )
    restored = await coord.async_restore_profile(payload)
    assert 13 in restored
    assert coord.calibrated_caps == restored
    assert coord.calibrated_meta["calibration_mode"] == "simple"
    assert coord.calibrated_meta["model"] == "Test Model"

    await coord.async_clear_profile()
    assert coord.calibrated_caps == {}
    assert coord.calibrated_meta == {}



