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

