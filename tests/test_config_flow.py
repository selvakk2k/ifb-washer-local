"""Unit tests for IFB Washer Local config flow."""

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
    hass.async_add_executor_job = AsyncMock(return_value=None)
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

        # 4. Select Model
        result4 = await flow.async_step_model({CONF_MODEL: "WD Executive ZXS"})
        assert result4["type"] == FlowResultType.FORM
        assert result4["step_id"] == "verify_phase1"

        # 5. Phase 1 Verification (Same side)
        result5 = await flow.async_step_verify_phase1({"verified": True})
        assert result5["type"] == FlowResultType.FORM
        assert result5["step_id"] == "verify_phase2"

        # 6. Phase 2 Verification (Opposite side)
        result6 = await flow.async_step_verify_phase2({"verified": True})
        assert result6["type"] == FlowResultType.CREATE_ENTRY
        assert result6["title"] == "IFB WD Executive ZXS (192.168.0.100)"
        assert result6["data"][CONF_HOST] == "192.168.0.100"
        assert result6["data"][CONF_PORT] == 80
        assert result6["data"][CONF_FAMILY] == ApplianceFamily.WASHER_DRYER
        assert result6["data"][CONF_MODEL] == "WD Executive ZXS"


@pytest.mark.asyncio
async def test_config_flow_custom_selection(mock_hass):
    """Test selecting custom family routes to custom step and creates entry."""
    flow = IFBWasherConfigFlow()
    flow.hass = mock_hass
    flow._host = "192.168.0.105"
    flow._port = 80

    # Select custom family
    result = await flow.async_step_machine_type({CONF_FAMILY: ApplianceFamily.CUSTOM})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "custom"

    # Submit custom step
    result2 = await flow.async_step_custom({})
    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"][CONF_FAMILY] == ApplianceFamily.CUSTOM


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
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "verify_phase1"
    assert flow._model == "Senator Smart Touch Custom"
