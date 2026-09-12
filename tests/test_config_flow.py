import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.ifb_washer_local.config_flow import IFBWasherConfigFlow
from custom_components.ifb_washer_local.const import (
    CONF_CUSTOM_MODEL,
    CONF_FAMILY,
    CONF_MODEL,
)
from ifb_washer_local import ApplianceFamily, WasherState


@pytest.fixture
def mock_hass():
    """Create a mocked HomeAssistant core instance."""
    hass = MagicMock()
    hass.data = {}
    hass.config.path = MagicMock(return_value="/tmp/ha_test_www/ifb_washer_local")

    async def _async_add_executor_job(target, *args, **kwargs):
        return target(*args, **kwargs)

    hass.async_add_executor_job = AsyncMock(side_effect=_async_add_executor_job)
    return hass


@pytest.mark.asyncio
async def test_config_flow_full_path(mock_hass):
    """Test full setup flow: user -> machine_type -> model -> verify_phase1 -> verify_phase2 -> entry created."""
    flow = IFBWasherConfigFlow()
    flow.hass = mock_hass

    # 1. Step User initial form
    result = await flow.async_step_user()
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    # 2. Submit Host
    mock_state = MagicMock(spec=WasherState)
    mock_state.program_code = 13  # Mix / Daily

    with (
        patch(
            "custom_components.ifb_washer_local.config_flow.IFBWasherClient.get_state",
            new_callable=AsyncMock,
            return_value=mock_state,
        ),
        patch(
            "custom_components.ifb_washer_local.config_flow.IFBWasherClient.select_program",
            new_callable=AsyncMock,
        ),
    ):

        with patch.object(flow, "async_set_unique_id", new_callable=AsyncMock):
            result2 = await flow.async_step_user({CONF_HOST: "192.168.0.100"})

        # Should transition to machine_type step
        assert result2["type"] == FlowResultType.FORM
        assert result2["step_id"] == "machine_type"

        # 3. Select Machine Type (Washer Dryer Refresher)
        result3 = await flow.async_step_machine_type({CONF_FAMILY: ApplianceFamily.WASHER_DRYER})
        assert result3["type"] == FlowResultType.FORM
        assert result3["step_id"] == "model"

        # 4. Select Model -> routes to verify_initial menu
        result4 = await flow.async_step_model({CONF_MODEL: "WD Executive ZXS"})
        assert result4["type"] == FlowResultType.MENU
        assert result4["step_id"] == "verify_initial"
        assert "verify_phase1" in result4["menu_options"]
        assert "skip_verification" in result4["menu_options"]

        # 5. Confirm Current Program button click -> routes to verify_phase1 menu (same side test)
        result5 = await flow.async_step_verify_phase1()
        assert result5["type"] == FlowResultType.MENU
        assert result5["step_id"] == "verify_phase1"
        assert "verify_phase2" in result5["menu_options"]
        assert "skip_verification" in result5["menu_options"]

        # 6. Same Side verification button click -> routes to verify_phase2 menu (opposite side test)
        result6 = await flow.async_step_verify_phase2()
        assert result6["type"] == FlowResultType.MENU
        assert result6["step_id"] == "verify_phase2"
        assert "finish_verification" in result6["menu_options"]
        assert "skip_verification" in result6["menu_options"]

        # 7. Opposite Side Finish Verification button click -> routes to calibrate step
        result7 = await flow.async_step_finish_verification()
        assert result7["type"] == FlowResultType.MENU
        assert result7["step_id"] == "calibrate"
        assert "calibrate_standard" in result7["menu_options"]
        assert "calibrate_quick" in result7["menu_options"]
        assert "calibrate_detailed" in result7["menu_options"]

        # 8. Select Standard Calibration -> creates entry immediately
        result8 = await flow.async_step_calibrate_standard()
        assert result8["type"] == FlowResultType.CREATE_ENTRY
        assert result8["title"] == "IFB WD Executive ZXS (192.168.0.100)"
        assert result8["data"][CONF_HOST] == "192.168.0.100"
        assert result8["data"][CONF_PORT] == 80
        assert result8["data"][CONF_FAMILY] == ApplianceFamily.WASHER_DRYER
        assert result8["data"][CONF_MODEL] == "WD Executive ZXS"


@pytest.mark.asyncio
async def test_config_flow_skip_verification(mock_hass):
    """Test clicking 'Skip Verification' in Phase 1 routes to calibrate step and standard creates entry."""
    flow = IFBWasherConfigFlow()
    flow.hass = mock_hass
    flow._host = "192.168.0.100"
    flow._port = 80
    flow._family = ApplianceFamily.WASHER_DRYER
    flow._model = "WD Executive ZXS"

    result = await flow.async_step_skip_verification()
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "calibrate"

    result2 = await flow.async_step_calibrate_standard()
    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"][CONF_MODEL] == "WD Executive ZXS"


@pytest.mark.asyncio
async def test_config_flow_custom_selection(mock_hass):
    """Test custom step routes to calibrate step and standard creates custom entry."""
    flow = IFBWasherConfigFlow()
    flow.hass = mock_hass
    flow._host = "192.168.0.105"
    flow._port = 80

    result = await flow.async_step_custom({})
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "calibrate"

    result2 = await flow.async_step_calibrate_standard()
    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"][CONF_FAMILY] == ApplianceFamily.CUSTOM


@pytest.mark.asyncio
async def test_config_flow_quick_calibration(mock_hass):
    """Test quick calibration execution during setup."""
    flow = IFBWasherConfigFlow()
    flow.hass = mock_hass
    flow._host = "192.168.0.100"
    flow._port = 80
    flow._family = ApplianceFamily.WASHER_DRYER
    flow._model = "WD Executive ZXS"

    mock_state = MagicMock(spec=WasherState)
    mock_state.is_running = False
    mock_state.is_paused = False

    with (
        patch(
            "custom_components.ifb_washer_local.config_flow.IFBWasherClient.get_state",
            new_callable=AsyncMock,
            return_value=mock_state,
        ),
        patch(
            "custom_components.ifb_washer_local.config_flow.calibrate_appliance_quick",
            new_callable=AsyncMock,
            return_value={},
        ),
    ):
        result = await flow.async_step_calibrate_quick()
        assert result["type"] == FlowResultType.SHOW_PROGRESS
        assert result["step_id"] == "calibrate_progress"

        progress_done = await flow.async_step_calibrate_progress()
        assert progress_done["type"] == FlowResultType.SHOW_PROGRESS_DONE

        finish_result = await flow.async_step_finish_calibration()
        assert finish_result["type"] == FlowResultType.CREATE_ENTRY
        assert finish_result["data"][CONF_MODEL] == "WD Executive ZXS"


@pytest.mark.asyncio
async def test_config_flow_simple_calibration(mock_hass):
    """Test simple calibration execution during setup."""
    flow = IFBWasherConfigFlow()
    flow.hass = mock_hass
    flow._host = "192.168.0.100"
    flow._port = 80
    flow._family = ApplianceFamily.WASHER_DRYER
    flow._model = "WD Executive ZXS"

    mock_state = MagicMock(spec=WasherState)
    mock_state.is_running = False
    mock_state.is_paused = False

    with (
        patch(
            "custom_components.ifb_washer_local.config_flow.IFBWasherClient.get_state",
            new_callable=AsyncMock,
            return_value=mock_state,
        ),
        patch(
            "custom_components.ifb_washer_local.config_flow.calibrate_appliance_simple",
            new_callable=AsyncMock,
            return_value={},
        ),
    ):
        result = await flow.async_step_calibrate_simple()
        assert result["type"] == FlowResultType.SHOW_PROGRESS
        assert result["step_id"] == "calibrate_progress"

        finish_result = await flow.async_step_finish_calibration()
        assert finish_result["type"] == FlowResultType.CREATE_ENTRY
        assert finish_result["data"][CONF_MODEL] == "WD Executive ZXS"



@pytest.mark.asyncio
async def test_config_flow_custom_model_text(mock_hass):
    """Test selecting 'custom' model routes to custom model text input."""
    flow = IFBWasherConfigFlow()
    flow.hass = mock_hass
    flow._host = "192.168.0.100"
    flow._port = 80
    flow._family = ApplianceFamily.WASHER_DRYER

    # Select "custom" in model dropdown
    result = await flow.async_step_model({CONF_MODEL: "custom"})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "custom_model_text"

    # Submit custom model name
    result2 = await flow.async_step_custom_model_text({CONF_CUSTOM_MODEL: "Senator Smart Touch Custom"})
    assert result2["type"] == FlowResultType.MENU
    assert result2["step_id"] == "verify_initial"
    assert flow._model == "Senator Smart Touch Custom"


@pytest.mark.asyncio
async def test_verification_skips_probe_when_running_or_paused(mock_hass):
    """Test that verification phases do not send select_program when washer is actively running."""
    flow = IFBWasherConfigFlow()
    flow.hass = mock_hass
    flow._host = "192.168.0.100"
    flow._port = 80
    flow._family = ApplianceFamily.WASHER_DRYER
    flow._model = "WD Executive ZXS"

    mock_state = MagicMock(spec=WasherState)
    mock_state.program_code = 13
    mock_state.is_running = True
    mock_state.is_paused = False

    flow._client = MagicMock()
    flow._client.get_state = AsyncMock(return_value=mock_state)
    flow._client.select_program = AsyncMock()

    # Phase 1
    await flow.async_step_verify_phase1()
    flow._client.select_program.assert_not_called()

    # Phase 2
    await flow.async_step_verify_phase2()
    flow._client.select_program.assert_not_called()


@pytest.mark.asyncio
async def test_verification_preserves_settings_when_idle(mock_hass):
    """Test that verification phases preserve current spin speed and temperature settings when probing."""
    flow = IFBWasherConfigFlow()
    flow.hass = mock_hass
    flow._host = "192.168.0.100"
    flow._port = 80
    flow._family = ApplianceFamily.WASHER_DRYER
    flow._model = "WD Executive ZXS"

    mock_state = MagicMock(spec=WasherState)
    mock_state.program_code = 13
    mock_state.is_running = False
    mock_state.is_paused = False
    mock_state.spin_speed_code = 4
    mock_state.temperature_code = 3

    flow._client = MagicMock()
    flow._client.get_state = AsyncMock(return_value=mock_state)
    flow._client.select_program = AsyncMock()

    # Phase 1: program 13 is in left_codes, candidate on left is chosen
    await flow.async_step_verify_phase1()
    _, kwargs = flow._client.select_program.call_args
    assert kwargs.get("spin_code", kwargs.get("spin_speed_code")) == 4
    assert kwargs.get("temp_code", kwargs.get("temperature_code")) == 3


@pytest.mark.asyncio
async def test_options_flow_init_and_save(mock_hass):
    """Test options flow initialization and saving without 500 attribute error."""
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_123"
    mock_entry.data = {
        CONF_HOST: "192.168.0.100",
        CONF_PORT: 80,
        CONF_FAMILY: ApplianceFamily.WASHER_DRYER,
        CONF_MODEL: "WD Executive ZXS",
    }
    mock_entry.options = {
        "scan_interval_standby": 15,
        "scan_interval_running": 5,
        CONF_MODEL: "WD Executive ZXS",
    }

    options_flow = IFBWasherConfigFlow.async_get_options_flow(mock_entry)
    options_flow.hass = mock_hass

    # Show form
    result = await options_flow.async_step_init()
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    # Submit form
    result2 = await options_flow.async_step_init({
        CONF_MODEL: "WD Executive ZXS Pro",
        "scan_interval_standby": 20,
        "scan_interval_running": 4,
        "calibration_action": "none",
    })
    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"][CONF_MODEL] == "WD Executive ZXS Pro"
    assert result2["data"]["scan_interval_standby"] == 20
    assert result2["data"]["scan_interval_running"] == 4


@pytest.mark.asyncio
async def test_options_flow_calibration_progress(mock_hass):
    """Test options flow calibration triggers async_show_progress cleanly."""
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_123"
    mock_entry.data = {
        CONF_HOST: "192.168.0.100",
        CONF_PORT: 80,
        CONF_FAMILY: ApplianceFamily.WASHER_DRYER,
        CONF_MODEL: "WD Executive ZXS",
    }
    mock_entry.options = {}

    mock_coordinator = MagicMock()
    mock_coordinator.async_calibrate = AsyncMock(return_value={})
    mock_hass.data = {"ifb_washer_local": {"test_entry_123": mock_coordinator}}

    options_flow = IFBWasherConfigFlow.async_get_options_flow(mock_entry)
    options_flow.hass = mock_hass

    # Select simple calibration in options
    result = await options_flow.async_step_init({
        CONF_MODEL: "WD Executive ZXS",
        "scan_interval_standby": 15,
        "scan_interval_running": 5,
        "calibration_action": "simple",
    })
    assert result["type"] == FlowResultType.SHOW_PROGRESS
    assert result["step_id"] == "calibrate_progress"

    # Progress done step
    progress_done = await options_flow.async_step_calibrate_progress()
    assert progress_done["type"] == FlowResultType.SHOW_PROGRESS_DONE

    # Finish step
    finish_result = await options_flow.async_step_finish_options()
    assert finish_result["type"] == FlowResultType.CREATE_ENTRY
    assert finish_result["data"][CONF_MODEL] == "WD Executive ZXS"


@pytest.mark.asyncio
async def test_options_flow_export_profile(mock_hass):
    """Test exporting calibrated profile from options flow."""
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_123"
    mock_entry.data = {
        CONF_HOST: "192.168.0.100",
        CONF_PORT: 80,
        CONF_FAMILY: ApplianceFamily.WASHER_DRYER,
        CONF_MODEL: "WD Executive ZXS",
        "calibrated_profile": {
            "13": {
                "allowed_temps": ["Cold", "40°C"],
                "allowed_spins": ["No Spin", "1000 RPM"],
                "supports_dry": False,
                "allowed_dry_modes": ["No Dry"],
                "supports_steam": True,
                "supports_prewash": True,
                "supports_soak": True,
                "supports_time_saver": True,
                "supports_extra_rinse": True,
                "supports_hot_rinse": True,
                "supports_rinse_hold": True,
                "supports_eco": True,
                "supports_aroma": True,
                "supports_anti_crease": True,
            }
        },
    }
    mock_entry.options = {}

    options_flow = IFBWasherConfigFlow.async_get_options_flow(mock_entry)
    options_flow.hass = mock_hass

    # Trigger export step
    result = await options_flow.async_step_init({
        CONF_MODEL: "WD Executive ZXS",
        "scan_interval_standby": 15,
        "scan_interval_running": 5,
        "calibration_action": "manage_profile",
    })
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "manage_profile"


@pytest.mark.asyncio
async def test_options_flow_restore_profile(mock_hass):
    """Test importing/restoring profile JSON in options flow."""
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_123"
    mock_entry.data = {
        CONF_HOST: "192.168.0.100",
        CONF_PORT: 80,
        CONF_FAMILY: ApplianceFamily.WASHER_DRYER,
        CONF_MODEL: "WD Executive ZXS",
    }
    mock_entry.options = {}

    mock_coordinator = MagicMock()
    mock_coordinator.calibrated_caps = {}
    mock_coordinator.calibrated_meta = {}
    mock_coordinator.async_restore_profile = AsyncMock(return_value={})
    mock_hass.data = {"ifb_washer_local": {"test_entry_123": mock_coordinator}}

    options_flow = IFBWasherConfigFlow.async_get_options_flow(mock_entry)
    options_flow.hass = mock_hass

    # Select restore action
    init_res = await options_flow.async_step_init({
        CONF_MODEL: "WD Executive ZXS",
        "scan_interval_standby": 15,
        "scan_interval_running": 5,
        "calibration_action": "manage_profile",
    })
    assert init_res["type"] == FlowResultType.FORM
    assert init_res["step_id"] == "manage_profile"

    # Submit valid profile JSON
    profile_json = json.dumps({
        "schema_version": 1,
        "calibration_mode": "simple",
        "model": "WD Executive ZXS",
        "capabilities": {
            "13": {
                "allowed_temps": ["Cold", "40°C"],
                "allowed_spins": ["No Spin", "1000 RPM"],
                "supports_dry": False,
                "allowed_dry_modes": ["No Dry"],
                "supports_steam": True,
                "supports_prewash": True,
                "supports_soak": True,
                "supports_time_saver": True,
                "supports_extra_rinse": True,
                "supports_hot_rinse": True,
                "supports_rinse_hold": True,
                "supports_eco": True,
                "supports_aroma": True,
                "supports_anti_crease": True,
            }
        },
    })
    restore_res = await options_flow.async_step_restore_profile({"profile_json": profile_json})
    assert restore_res["type"] == FlowResultType.CREATE_ENTRY
    mock_coordinator.async_restore_profile.assert_awaited_once()


@pytest.mark.asyncio
async def test_config_flow_with_custom_name(mock_hass):
    """Test config flow creating entry with custom friendly name."""
    from homeassistant.const import CONF_NAME
    flow = IFBWasherConfigFlow()
    flow.hass = mock_hass

    mock_state = MagicMock(spec=WasherState)
    mock_state.program_code = 13

    with (
        patch(
            "custom_components.ifb_washer_local.config_flow.IFBWasherClient.get_state",
            new_callable=AsyncMock,
            return_value=mock_state,
        ),
        patch.object(flow, "async_set_unique_id", new_callable=AsyncMock),
    ):
        result = await flow.async_step_user({
            CONF_HOST: "192.168.0.105",
            CONF_PORT: 80,
            CONF_NAME: "Laundry Room Washer",
        })
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "machine_type"

        result = await flow.async_step_machine_type({CONF_FAMILY: ApplianceFamily.WASHER_DRYER})
        assert result["type"] == FlowResultType.FORM

        result = await flow.async_step_model({CONF_MODEL: "WD Executive ZXS"})
        assert result["type"] == FlowResultType.MENU

        result = await flow.async_step_calibrate_standard()
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "Laundry Room Washer"
        assert result["data"][CONF_NAME] == "Laundry Room Washer"


@pytest.mark.asyncio
async def test_setup_entry_registers_update_listener_and_reload(mock_hass):
    """Test that async_setup_entry registers an update listener and async_reload_entry reloads config entry."""
    from custom_components.ifb_washer_local import async_reload_entry, async_setup_entry

    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_123"
    mock_entry.data = {CONF_HOST: "192.168.0.100", CONF_PORT: 80}
    mock_entry.options = {}
    mock_entry.async_on_unload = MagicMock()
    mock_entry.add_update_listener = MagicMock(return_value="listener_unsub")

    mock_hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
    mock_hass.config_entries.async_reload = AsyncMock(return_value=True)

    with (
        patch(
            "custom_components.ifb_washer_local.coordinator.IFBWasherCoordinator.async_config_entry_first_refresh",
            new_callable=AsyncMock,
        ),
    ):
        result = await async_setup_entry(mock_hass, mock_entry)
        assert result is True
        mock_entry.add_update_listener.assert_called_once_with(async_reload_entry)
        mock_entry.async_on_unload.assert_called_with("listener_unsub")

        # Test reload helper
        await async_reload_entry(mock_hass, mock_entry)
        mock_hass.config_entries.async_reload.assert_awaited_once_with("test_entry_123")


@pytest.mark.asyncio
async def test_setup_entry_prewarms_models_lookup(mock_hass):
    """Test that async_setup_entry invokes async_add_executor_job to pre-warm the catalog."""
    from custom_components.ifb_washer_local import async_setup_entry

    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_prewarm"
    mock_entry.data = {CONF_HOST: "192.168.0.100", CONF_PORT: 80}
    mock_entry.options = {}
    mock_entry.async_on_unload = MagicMock()
    mock_entry.add_update_listener = MagicMock()

    mock_hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)

    with (
        patch(
            "custom_components.ifb_washer_local.coordinator.IFBWasherCoordinator.async_config_entry_first_refresh",
            new_callable=AsyncMock,
        ),
    ):
        result = await async_setup_entry(mock_hass, mock_entry)
        assert result is True
        mock_hass.async_add_executor_job.assert_called()


@pytest.mark.asyncio
async def test_dhcp_discovery_stored_mac_match(mock_hass):
    """Test DHCP discovery matching by stored MAC address updates host and coordinator."""
    from dataclasses import dataclass
    from custom_components.ifb_washer_local.const import CONF_MAC_ADDRESS, DOMAIN

    @dataclass
    class FakeDhcpServiceInfo:
        ip: str
        macaddress: str
        hostname: str = ""

    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_123"
    mock_entry.unique_id = "20f85e5d590b"
    mock_entry.data = {
        CONF_HOST: "192.168.0.100",
        CONF_PORT: 80,
        CONF_MAC_ADDRESS: "20:f8:5e:5d:59:0b",
    }

    mock_coordinator = MagicMock()
    mock_coordinator.client = MagicMock()
    mock_coordinator.client.host = "192.168.0.100"
    mock_coordinator.async_request_refresh = AsyncMock()

    mock_hass.data = {DOMAIN: {"test_entry_123": mock_coordinator}}
    mock_hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])

    flow = IFBWasherConfigFlow()
    flow.hass = mock_hass

    discovery_info = FakeDhcpServiceInfo(ip="192.168.0.105", macaddress="20:f8:5e:5d:59:0b")
    result = await flow.async_step_dhcp(discovery_info)

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert mock_coordinator.client.host == "192.168.0.105"
    mock_hass.config_entries.async_update_entry.assert_called_once()
    updated_data = mock_hass.config_entries.async_update_entry.call_args[1]["data"]
    assert updated_data[CONF_HOST] == "192.168.0.105"
    assert updated_data[CONF_MAC_ADDRESS] == "20:f8:5e:5d:59:0b"


@pytest.mark.asyncio
async def test_dhcp_discovery_same_ip_mac_adoption(mock_hass):
    """Test DHCP discovery adopting MAC address when IP matches existing configured entry."""
    from dataclasses import dataclass
    from custom_components.ifb_washer_local.const import CONF_MAC_ADDRESS, DOMAIN

    @dataclass
    class FakeDhcpServiceInfo:
        ip: str
        macaddress: str
        hostname: str = ""

    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_same_ip"
    mock_entry.unique_id = "192.168.0.100"
    mock_entry.data = {
        CONF_HOST: "192.168.0.100",
        CONF_PORT: 80,
    }

    mock_coordinator = MagicMock()
    mock_coordinator.client = MagicMock()
    mock_coordinator.client.host = "192.168.0.100"
    mock_coordinator.async_request_refresh = AsyncMock()

    mock_hass.data = {DOMAIN: {"test_entry_same_ip": mock_coordinator}}
    mock_hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])

    flow = IFBWasherConfigFlow()
    flow.hass = mock_hass

    discovery_info = FakeDhcpServiceInfo(ip="192.168.0.100", macaddress="20:f8:5e:5d:59:0b")
    result = await flow.async_step_dhcp(discovery_info)

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    mock_hass.config_entries.async_update_entry.assert_called_once()
    call_kwargs = mock_hass.config_entries.async_update_entry.call_args[1]
    assert call_kwargs["data"][CONF_MAC_ADDRESS] == "20:f8:5e:5d:59:0b"
    assert call_kwargs["unique_id"] == "20f85e5d590b"


@pytest.mark.asyncio
async def test_dhcp_discovery_probe_fallback(mock_hass):
    """Test DHCP discovery fallback probing new IP when entry has no stored MAC."""
    from dataclasses import dataclass
    from custom_components.ifb_washer_local.const import CONF_MAC_ADDRESS, DOMAIN

    @dataclass
    class FakeDhcpServiceInfo:
        ip: str
        macaddress: str
        hostname: str = ""

    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_probe"
    mock_entry.unique_id = "192.168.0.100"
    mock_entry.data = {
        CONF_HOST: "192.168.0.100",
        CONF_PORT: 80,
    }

    mock_coordinator = MagicMock()
    mock_coordinator.client = MagicMock()
    mock_coordinator.client.host = "192.168.0.100"
    mock_coordinator.async_request_refresh = AsyncMock()

    mock_hass.data = {DOMAIN: {"test_entry_probe": mock_coordinator}}
    mock_hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])

    flow = IFBWasherConfigFlow()
    flow.hass = mock_hass

    mock_state = MagicMock(spec=WasherState)
    mock_state.program_code = 13

    with patch(
        "custom_components.ifb_washer_local.config_flow.IFBWasherClient.get_state",
        new_callable=AsyncMock,
        return_value=mock_state,
    ):
        discovery_info = FakeDhcpServiceInfo(ip="192.168.0.105", macaddress="20:f8:5e:5d:59:0b")
        result = await flow.async_step_dhcp(discovery_info)

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert mock_coordinator.client.host == "192.168.0.105"
    mock_hass.config_entries.async_update_entry.assert_called_once()
    call_kwargs = mock_hass.config_entries.async_update_entry.call_args[1]
    assert call_kwargs["data"][CONF_HOST] == "192.168.0.105"
    assert call_kwargs["data"][CONF_MAC_ADDRESS] == "20:f8:5e:5d:59:0b"
    assert call_kwargs["unique_id"] == "20f85e5d590b"


@pytest.mark.asyncio
async def test_options_flow_set_mac_address(mock_hass):
    """Test setting MAC address manually via options flow."""
    from custom_components.ifb_washer_local.const import CONF_MAC_ADDRESS

    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_opts_mac"
    mock_entry.unique_id = "192.168.0.100"
    mock_entry.data = {
        CONF_HOST: "192.168.0.100",
        CONF_PORT: 80,
        CONF_MODEL: "WD Executive ZXS",
    }
    mock_entry.options = {}

    options_flow = IFBWasherConfigFlow.async_get_options_flow(mock_entry)
    options_flow.hass = mock_hass

    result = await options_flow.async_step_init({
        CONF_MODEL: "WD Executive ZXS",
        CONF_MAC_ADDRESS: "20:f8:5e:5d:59:0b",
        "scan_interval_standby": 15,
        "scan_interval_running": 5,
        "calibration_action": "none",
    })

    assert result["type"] == FlowResultType.CREATE_ENTRY
    mock_hass.config_entries.async_update_entry.assert_called_once()
    call_kwargs = mock_hass.config_entries.async_update_entry.call_args[1]
    assert call_kwargs["data"][CONF_MAC_ADDRESS] == "20:f8:5e:5d:59:0b"
    assert call_kwargs["unique_id"] == "20f85e5d590b"


@pytest.mark.asyncio
async def test_reconfigure_flow(mock_hass):
    """Test reconfiguring washer host IP."""
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_reconf"
    mock_entry.data = {
        CONF_HOST: "192.168.0.100",
        CONF_PORT: 80,
    }
    mock_hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)
    mock_hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])

    flow = IFBWasherConfigFlow()
    flow.hass = mock_hass
    flow.context = {"entry_id": "test_entry_reconf"}

    # Initial form
    form_result = await flow.async_step_reconfigure()
    assert form_result["type"] == FlowResultType.FORM
    assert form_result["step_id"] == "reconfigure"

    # Submit new host
    with patch(
        "custom_components.ifb_washer_local.config_flow.IFBWasherClient.get_state",
        new_callable=AsyncMock,
        side_effect=Exception("Unreachable in standby"),
    ):
        result = await flow.async_step_reconfigure({
            CONF_HOST: "192.168.0.160",
            CONF_PORT: 80,
        })

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"


@pytest.mark.asyncio
async def test_options_flow_update_host(mock_hass):
    """Test manually updating host IP in options flow."""
    from custom_components.ifb_washer_local.const import DOMAIN

    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_opts_host"
    mock_entry.unique_id = "20f85e5d590b"
    mock_entry.data = {
        CONF_HOST: "192.168.0.100",
        CONF_PORT: 80,
        CONF_MODEL: "WD Executive ZXS",
    }
    mock_entry.options = {}

    mock_coordinator = MagicMock()
    mock_coordinator.client = MagicMock()
    mock_coordinator.client.host = "192.168.0.100"
    mock_coordinator.async_request_refresh = AsyncMock()
    mock_hass.data = {DOMAIN: {"test_entry_opts_host": mock_coordinator}}

    options_flow = IFBWasherConfigFlow.async_get_options_flow(mock_entry)
    options_flow.hass = mock_hass

    result = await options_flow.async_step_init({
        CONF_HOST: "192.168.0.160",
        CONF_MODEL: "WD Executive ZXS",
        "scan_interval_standby": 15,
        "scan_interval_running": 5,
        "calibration_action": "none",
    })

    assert result["type"] == FlowResultType.CREATE_ENTRY
    mock_hass.config_entries.async_update_entry.assert_called_once()
    call_kwargs = mock_hass.config_entries.async_update_entry.call_args[1]
    assert call_kwargs["data"][CONF_HOST] == "192.168.0.160"
    assert mock_coordinator.client.host == "192.168.0.160"
    mock_coordinator.async_request_refresh.assert_called_once()






