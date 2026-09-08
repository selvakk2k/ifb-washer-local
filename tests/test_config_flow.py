"""Unit tests for IFB Washer Local config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.ifb_washer_local.config_flow import IFBWasherConfigFlow
from custom_components.ifb_washer_local.const import CONF_FAMILY
from ifb_washer_local import ApplianceFamily, WasherState


@pytest.fixture
def mock_hass():
    """Create a mocked HomeAssistant core instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    return hass


@pytest.mark.asyncio
async def test_config_flow_full_path(mock_hass):
    """Test full setup flow: user -> family -> verify -> entry created."""
    flow = IFBWasherConfigFlow()
    flow.hass = mock_hass



    # 1. Step User initial form
    result = await flow.async_step_user()
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    # 2. Submit Host
    mock_state = MagicMock(spec=WasherState)
    with (
        patch("custom_components.ifb_washer_local.config_flow.async_get_clientsession"),
        patch("custom_components.ifb_washer_local.config_flow.IFBWasherClient") as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.get_state.return_value = mock_state
        mock_client.select_program.return_value = mock_state
        mock_client_cls.return_value = mock_client

        with patch.object(flow, "async_set_unique_id", new_callable=AsyncMock):
            result2 = await flow.async_step_user({CONF_HOST: "192.168.0.100"})


        # Should transition to family step
        assert result2["type"] == FlowResultType.FORM
        assert result2["step_id"] == "family"

        # 3. Select Family
        result3 = await flow.async_step_family({CONF_FAMILY: ApplianceFamily.WASHER_DRYER})
        assert result3["type"] == FlowResultType.FORM
        assert result3["step_id"] == "verify"

        # 4. Verify step submission
        result4 = await flow.async_step_verify({"verified": True, "skip_verification": False})
        assert result4["type"] == FlowResultType.CREATE_ENTRY
        assert result4["title"] == "IFB Washer (192.168.0.100)"
        assert result4["data"][CONF_HOST] == "192.168.0.100"
        assert result4["data"][CONF_PORT] == 80
        assert result4["data"][CONF_FAMILY] == ApplianceFamily.WASHER_DRYER


@pytest.mark.asyncio
async def test_config_flow_custom_selection(mock_hass):
    """Test selecting custom family routes to custom step and creates entry."""
    flow = IFBWasherConfigFlow()
    flow.hass = mock_hass
    flow._host = "192.168.0.105"
    flow._port = 80

    # Select custom family
    result = await flow.async_step_family({CONF_FAMILY: ApplianceFamily.CUSTOM})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "custom"

    # Submit custom step
    result2 = await flow.async_step_custom({})
    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"][CONF_FAMILY] == ApplianceFamily.CUSTOM
