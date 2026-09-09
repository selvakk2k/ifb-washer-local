"""Unit tests for IFB Washer Local coordinator calculations and sensors."""

from datetime import datetime
from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant

from custom_components.ifb_washer_local.const import (
    CONF_FAMILY,
    DEFAULT_FAMILY,
)
from custom_components.ifb_washer_local.coordinator import IFBWasherCoordinator
from ifb_washer_local import ApplianceFamily, WasherState


def create_mock_state(
    is_running: bool = True,
    remaining_minutes: int = 60,
    has_problem: bool = False,
    error_code: str = "",
    error_description: str = "",
    is_complete: bool = False,
    cycle_progress: float = 0.0,
) -> WasherState:
    """Helper to construct a mock WasherState."""
    state = MagicMock(spec=WasherState)
    state.is_running = is_running
    state.remaining_minutes = remaining_minutes
    state.has_problem = has_problem
    state.error_code = error_code
    state.error_description = error_description
    state.is_complete = is_complete
    state.cycle_progress = cycle_progress
    return state


def test_coordinator_progress_calculation():
    """Verify cycle progress percentage calculation."""
    hass = MagicMock(spec=HomeAssistant)
    client = MagicMock()
    client.host = "192.168.0.100"

    coord = IFBWasherCoordinator(hass, client)
    coord._initial_cycle_duration = 120

    # Running with 60 minutes remaining -> 50%
    coord.data = create_mock_state(is_running=True, remaining_minutes=60)
    assert coord.cycle_progress == 50.0

    # Running with 30 minutes remaining -> 75%
    coord.data = create_mock_state(is_running=True, remaining_minutes=30)
    assert coord.cycle_progress == 75.0

    # Running with 0 minutes remaining -> 100%
    coord.data = create_mock_state(is_running=True, remaining_minutes=0)
    assert coord.cycle_progress == 100.0

    # When idle/not running, progress is None
    coord.data = create_mock_state(is_running=False, remaining_minutes=0)
    assert coord.cycle_progress is None


def test_coordinator_estimated_end_time():
    """Verify estimated end time timestamp calculation."""
    hass = MagicMock(spec=HomeAssistant)
    client = MagicMock()
    client.host = "192.168.0.100"

    coord = IFBWasherCoordinator(hass, client)

    # When running with remaining time
    coord.data = create_mock_state(is_running=True, remaining_minutes=45)
    end_time = coord.estimated_end_time
    assert end_time is not None
    assert isinstance(end_time, datetime)

    # When idle/not running
    coord.data = create_mock_state(is_running=False, remaining_minutes=0)
    assert coord.estimated_end_time is None


def test_coordinator_device_info_models():
    """Verify device model string resolution by family."""
    hass = MagicMock(spec=HomeAssistant)
    client = MagicMock()
    client.host = "192.168.0.100"

    # Washer Dryer family
    entry_wd = MagicMock()
    entry_wd.data = {CONF_FAMILY: ApplianceFamily.WASHER_DRYER}
    coord_wd = IFBWasherCoordinator(hass, client, entry=entry_wd)
    assert "Washer Dryer" in coord_wd.device_info["model"]

    # Front load family
    entry_fl = MagicMock()
    entry_fl.data = {CONF_FAMILY: ApplianceFamily.FRONT_LOAD}
    coord_fl = IFBWasherCoordinator(hass, client, entry=entry_fl)
    assert "Front Load" in coord_fl.device_info["model"]

    # Top load family
    entry_tl = MagicMock()
    entry_tl.data = {CONF_FAMILY: ApplianceFamily.TOP_LOAD_SMART}
    coord_tl = IFBWasherCoordinator(hass, client, entry=entry_tl)
    assert "Top Load" in coord_tl.device_info["model"]


def test_problem_binary_sensor():
    """Verify problem binary sensor status and attributes."""
    from custom_components.ifb_washer_local.binary_sensor import (
        BINARY_SENSOR_TYPES,
        IFBWasherBinarySensor,
    )

    hass = MagicMock(spec=HomeAssistant)
    client = MagicMock()
    client.host = "192.168.0.100"
    coord = IFBWasherCoordinator(hass, client)

    problem_desc = next(d for d in BINARY_SENSOR_TYPES if d.key == "problem")
    sensor = IFBWasherBinarySensor(coord, problem_desc)

    # Normal state - no error
    coord.data = create_mock_state(has_problem=False, error_code="", error_description="")
    assert sensor.is_on is False
    assert sensor.extra_state_attributes == {"error_code": "", "error_description": ""}

    # Fault state - Tap closed
    coord.data = create_mock_state(
        has_problem=True, error_code="tAP", error_description="Water Tap Closed"
    )
    assert sensor.is_on is True
    assert sensor.extra_state_attributes == {
        "error_code": "tAP",
        "error_description": "Water Tap Closed",
    }


def test_program_select_options_by_family():
    """Verify program selector options adapt to the configured family."""
    from custom_components.ifb_washer_local.select import IFBWasherProgramSelect

    hass = MagicMock(spec=HomeAssistant)
    client = MagicMock()
    client.host = "192.168.0.100"

    # Washer Dryer family
    entry_wd = MagicMock()
    entry_wd.data = {CONF_FAMILY: ApplianceFamily.WASHER_DRYER}
    coord_wd = IFBWasherCoordinator(hass, client, entry=entry_wd)
    select_wd = IFBWasherProgramSelect(coord_wd)
    assert "Wash + Dry 2Hr" in select_wd.options
    assert "Mix / Daily" in select_wd.options

    # Front Load family
    entry_fl = MagicMock()
    entry_fl.data = {CONF_FAMILY: ApplianceFamily.FRONT_LOAD}
    coord_fl = IFBWasherCoordinator(hass, client, entry=entry_fl)
    select_fl = IFBWasherProgramSelect(coord_fl)
    assert "Uniform / Linen" in select_fl.options
    assert "Sports Wear" in select_fl.options


def test_temperature_select_and_sensor_none():
    """Verify temperature selector and sensor properly handle code 0 as None."""
    from custom_components.ifb_washer_local.select import IFBWasherTemperatureSelect
    from custom_components.ifb_washer_local.sensor import SENSOR_TYPES, IFBWasherSensor

    hass = MagicMock(spec=HomeAssistant)
    client = MagicMock()
    client.host = "192.168.0.100"
    coord = IFBWasherCoordinator(hass, client)

    temp_select = IFBWasherTemperatureSelect(coord)
    assert "None" in temp_select.options
    assert "40°C" in temp_select.options

    # Machine on Refresh / Steam (code 0 -> "None")
    state = create_mock_state()
    state.temperature_code = 0
    state.temperature_name = "None"
    coord.data = state
    assert temp_select.current_option == "None"

    # Verify sensor also reports None
    temp_sensor_desc = next(d for d in SENSOR_TYPES if d.key == "temperature_setting")
    sensor = IFBWasherSensor(coord, temp_sensor_desc)
    assert sensor.native_value == "None"


async def test_program_select_async_set_updated_data():
    """Verify selecting a program updates coordinator data directly without refresh bounce."""
    from unittest.mock import AsyncMock
    from custom_components.ifb_washer_local.select import IFBWasherProgramSelect

    hass = MagicMock(spec=HomeAssistant)
    client = MagicMock()
    client.host = "192.168.0.100"
    updated_state = create_mock_state(is_running=False, remaining_minutes=72)
    updated_state.program_code = 13
    updated_state.program_name = "Mix / Daily"
    client.select_program = AsyncMock(return_value=updated_state)

    coord = IFBWasherCoordinator(hass, client)
    coord.async_set_updated_data = MagicMock()
    coord.async_request_refresh = AsyncMock()

    select = IFBWasherProgramSelect(coord)
    await select.async_select_option("Mix / Daily")

    client.select_program.assert_awaited_once_with(13)
    coord.async_set_updated_data.assert_called_once_with(updated_state)
    coord.async_request_refresh.assert_not_called()


def test_time_remaining_and_program_duration_sensors():
    """Verify time_remaining is gated by run state and program_duration reports total duration."""
    from custom_components.ifb_washer_local.sensor import SENSOR_TYPES, IFBWasherSensor

    hass = MagicMock(spec=HomeAssistant)
    client = MagicMock()
    client.host = "192.168.0.100"
    coord = IFBWasherCoordinator(hass, client)

    time_rem_desc = next(d for d in SENSOR_TYPES if d.key == "time_remaining")
    prog_dur_desc = next(d for d in SENSOR_TYPES if d.key == "program_duration")
    time_rem_sensor = IFBWasherSensor(coord, time_rem_desc)
    prog_dur_sensor = IFBWasherSensor(coord, prog_dur_desc)

    # 1. Standby state (is_running=False, is_paused=False, remaining=72)
    state = create_mock_state(is_running=False, remaining_minutes=72)
    state.is_paused = False
    state.total_program_minutes = 72
    coord.data = state

    assert time_rem_sensor.native_value == 0
    assert time_rem_sensor.extra_state_attributes == {
        "program_duration": 72,
        "display_minutes": 72,
    }
    assert prog_dur_sensor.native_value == 72

    # 2. Running state (is_running=True, remaining=55)
    state_running = create_mock_state(is_running=True, remaining_minutes=55)
    state_running.is_paused = False
    state_running.total_program_minutes = 72
    coord.data = state_running

    assert time_rem_sensor.native_value == 55
    assert prog_dur_sensor.native_value == 72

    # 3. Paused state (is_running=False, is_paused=True, remaining=30)
    state_paused = create_mock_state(is_running=False, remaining_minutes=30)
    state_paused.is_paused = True
    state_paused.total_program_minutes = 72
    coord.data = state_paused

    assert time_rem_sensor.native_value == 30
    assert prog_dur_sensor.native_value == 72


async def test_delay_start_options_and_select():
    """Verify delay start selector options and command code mapping."""
    from unittest.mock import AsyncMock
    from custom_components.ifb_washer_local.select import IFBWasherDelayStartSelect

    hass = MagicMock(spec=HomeAssistant)
    client = MagicMock()
    client.host = "192.168.0.100"
    updated_state = create_mock_state()
    updated_state.delay_start_minutes = 120
    client.set_delay_start = AsyncMock(return_value=updated_state)

    coord = IFBWasherCoordinator(hass, client)
    coord.async_set_updated_data = MagicMock()

    select = IFBWasherDelayStartSelect(coord)
    assert "No Delay" in select.options
    assert "30 Minutes" in select.options
    assert "1 Hour" in select.options
    assert "2 Hours" in select.options
    assert "19 Hours" in select.options
    assert "20 Hours" not in select.options

    # 1. 0 minutes -> No Delay
    state = create_mock_state()
    state.delay_start_minutes = 0
    coord.data = state
    assert select.current_option == "No Delay"

    # 2. 30 minutes -> 30 Minutes
    state.delay_start_minutes = 30
    assert select.current_option == "30 Minutes"

    # 3. 120 minutes -> 2 Hours
    state.delay_start_minutes = 120
    assert select.current_option == "2 Hours"

    # 4. Selecting "2 Hours" sends hardware code 4
    await select.async_select_option("2 Hours")
    client.set_delay_start.assert_awaited_once_with(4)
    coord.async_set_updated_data.assert_called_once_with(updated_state)

    # 5. Selecting "30 Minutes" sends hardware code 1
    client.set_delay_start.reset_mock()
    await select.async_select_option("30 Minutes")
    client.set_delay_start.assert_awaited_once_with(1)

    # 6. Selecting "No Delay" sends hardware code 0
    client.set_delay_start.reset_mock()
    await select.async_select_option("No Delay")
    client.set_delay_start.assert_awaited_once_with(0)


async def test_power_switch():
    """Verify power switch state reporting and turn_on/turn_off actions."""
    from unittest.mock import AsyncMock
    from custom_components.ifb_washer_local.switch import IFBWasherPowerSwitch

    hass = MagicMock(spec=HomeAssistant)
    client = MagicMock()
    client.host = "192.168.0.100"
    state_on = create_mock_state()
    state_on.is_powered_on = True
    state_off = create_mock_state()
    state_off.is_powered_on = False

    client.power_on = AsyncMock(return_value=state_on)
    client.power_off = AsyncMock(return_value=state_off)

    coord = IFBWasherCoordinator(hass, client)
    coord.async_set_updated_data = MagicMock()

    power_switch = IFBWasherPowerSwitch(coord)
    assert power_switch.icon == "mdi:power"

    # When powered on
    coord.data = state_on
    assert power_switch.is_on is True

    # When powered off
    coord.data = state_off
    assert power_switch.is_on is False

    # Turn on
    await power_switch.async_turn_on()
    client.power_on.assert_awaited_once()
    coord.async_set_updated_data.assert_called_once_with(state_on)

    # Turn off
    coord.async_set_updated_data.reset_mock()
    await power_switch.async_turn_off()
    client.power_off.assert_awaited_once()
    coord.async_set_updated_data.assert_called_once_with(state_off)





