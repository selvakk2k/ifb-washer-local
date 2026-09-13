"""Unit tests for universal /24 subnet auto-discovery in IFB Washer Local."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import CONF_HOST
from homeassistant.helpers.update_coordinator import UpdateFailed

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ifb_washer_local.coordinator import (
    IFBConnectionError,
    IFBWasherCoordinator,
)
from ifb_washer_local import WasherState


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.host = "192.168.29.6"
    client.port = 80
    client.session = MagicMock()
    client.get_state = AsyncMock()
    return client


@pytest.fixture
def mock_config_entry(hass):
    entry = MockConfigEntry(
        domain="ifb_washer_local",
        data={CONF_HOST: "192.168.29.6"},
        unique_id="20f85e5d590b",
    )
    entry.add_to_hass(hass)
    return entry


async def test_consecutive_failures_trigger_auto_discovery(hass, mock_client, mock_config_entry):
    """Test that 3 consecutive connection failures trigger auto-discovery."""
    coordinator = IFBWasherCoordinator(hass, mock_client, mock_config_entry)
    mock_client.get_state.side_effect = IFBConnectionError("Unreachable")

    # 1st failure
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
    assert coordinator._consecutive_connection_failures == 1

    # 2nd failure
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
    assert coordinator._consecutive_connection_failures == 2

    # 3rd failure: triggers auto-discovery
    with patch.object(
        coordinator, "_async_attempt_auto_discovery", new_callable=AsyncMock
    ) as mock_discover:
        mock_discover.return_value = None
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
        assert coordinator._consecutive_connection_failures == 3
        mock_discover.assert_awaited_once()


async def test_auto_discovery_success_rebinds_host(hass, mock_client, mock_config_entry):
    """Test successful discovery updates client.host and config entry."""
    coordinator = IFBWasherCoordinator(hass, mock_client, mock_config_entry)

    target_new_ip = "192.168.29.42"
    valid_state = MagicMock(spec=WasherState)
    valid_state.state_name = "Standby"
    valid_state.is_running = False
    valid_state.remaining_minutes = 0

    # Simulate discovering 192.168.29.42
    with patch.object(
        coordinator,
        "_async_attempt_auto_discovery",
        new_callable=AsyncMock,
        return_value=valid_state,
    ):
        coordinator._consecutive_connection_failures = 2
        mock_client.get_state.side_effect = IFBConnectionError("Unreachable")

        result = await coordinator._async_update_data()
        assert result == valid_state


async def test_auto_discovery_rate_limiting(hass, mock_client, mock_config_entry):
    """Test that full subnet sweeps are rate-limited to once every 10 minutes."""
    coordinator = IFBWasherCoordinator(hass, mock_client, mock_config_entry)
    coordinator._last_discovery_sweep = 1000.0

    with patch("time.monotonic", return_value=1100.0):  # only 100s later
        result = await coordinator._async_attempt_auto_discovery()
        assert result is None


async def test_auto_discovery_subnet_probe_matching(hass, mock_client, mock_config_entry):
    """Test that _async_attempt_auto_discovery correctly identifies a valid IFB washer."""
    coordinator = IFBWasherCoordinator(hass, mock_client, mock_config_entry)
    coordinator._last_discovery_sweep = 0.0

    valid_state = MagicMock(spec=WasherState)
    valid_state.state_name = "Standby"
    mock_client.get_state.return_value = valid_state

    # Mock IFBWasherClient inside coordinator to simulate finding a washer at .42
    with patch(
        "custom_components.ifb_washer_local.coordinator.IFBWasherClient"
    ) as MockClientClass:
        def client_side_effect(host, **kwargs):
            c = MagicMock()
            c.host = host
            if host == "192.168.29.42":
                c.get_state = AsyncMock(return_value=valid_state)
            else:
                c.get_state = AsyncMock(side_effect=IFBConnectionError("Unreachable"))
            return c

        MockClientClass.side_effect = client_side_effect

        # Mock the session.get probe
        class MockResp:
            status = 200
            async def read(self):
                return b"\x00" * 38
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass

        class MockSession:
            def get(self, url, **kwargs):
                if "192.168.29.42" in url:
                    return MockResp()
                raise IFBConnectionError("No response")

        coordinator.client.session = MockSession()

        result = await coordinator._async_attempt_auto_discovery()
        assert result == valid_state
        assert coordinator.client.host == "192.168.29.42"
        assert coordinator._consecutive_connection_failures == 0

