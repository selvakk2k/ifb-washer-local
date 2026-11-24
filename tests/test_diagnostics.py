"""Unit tests for IFB Washer Local diagnostics."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock

import pytest

from tests.ha_stub import setup_ha_stubs

setup_ha_stubs()

from custom_components.ifb_washer_local.const import (  # noqa: E402
    CONF_MAC_ADDRESS,
    DOMAIN,
)
from custom_components.ifb_washer_local.diagnostics import (  # noqa: E402
    async_get_config_entry_diagnostics,
)
from ifb_washer_local.protocol import WasherState  # noqa: E402


@pytest.mark.asyncio
async def test_diagnostics_with_coordinator():
    """Test diagnostics returns expected structure and redacts sensitive data."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_entry_456"
    entry.version = 1
    entry.domain = DOMAIN
    entry.title = "IFB Senator W/D"
    entry.pref_disable_new_entities = False
    entry.pref_disable_polling = False
    entry.data = {
        "host": "192.168.1.100",
        "port": 80,
        CONF_MAC_ADDRESS: "20:F8:5E:AA:BB:CC",
        "family": "washer_dryer",
        "model": "Senator Smart Touch",
    }
    entry.options = {
        "scan_interval_standby": 60,
        "scan_interval_running": 5,
    }

    mock_coordinator = MagicMock()
    mock_coordinator.last_update_success = True
    mock_coordinator.is_connected = True
    mock_coordinator.appliance_family = "washer_dryer"
    mock_coordinator.model_name = "Senator Smart Touch"
    mock_coordinator.device_name = "IFB Senator W/D"
    mock_coordinator.update_interval = timedelta(seconds=60)
    mock_coordinator.data = WasherState(
        program_code=13,
        program_name="Mix / Daily",
        remaining_minutes=42,
        state_code=2,
        state_name="Running",
        door_locked=True,
        child_lock=False,
        spin_speed_code=1200,
        spin_speed_name="1200 RPM",
        temperature_code=40,
        temperature_name="40 C",
        motor_rpm=800,
        tub_temperature_c=38,
        raw_hex="0102030405060708090a0b0c",
    )

    entry.runtime_data = mock_coordinator

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["entry"]["entry_id"] == "test_entry_456"
    assert diagnostics["entry"]["data"]["host"] == "**REDACTED**"
    assert diagnostics["entry"]["data"][CONF_MAC_ADDRESS] == "**REDACTED**"
    assert diagnostics["entry"]["data"]["family"] == "washer_dryer"

    coord = diagnostics["coordinator"]
    assert coord["last_update_success"] is True
    assert coord["connected"] is True
    assert coord["family"] == "washer_dryer"
    assert coord["model"] == "Senator Smart Touch"
    assert coord["device_name"] == "IFB Senator W/D"
    assert coord["update_interval_seconds"] == 60.0
    assert coord["state"]["program_name"] == "Mix / Daily"
    assert coord["state"]["remaining_minutes"] == 42


@pytest.mark.asyncio
async def test_diagnostics_without_coordinator():
    """Test diagnostics works gracefully when coordinator is not yet loaded."""
    hass = MagicMock()
    hass.data = {}
    entry = MagicMock()
    entry.entry_id = "test_entry_no_coord"
    entry.version = 1
    entry.domain = DOMAIN
    entry.title = "IFB Washer Unconnected"
    entry.pref_disable_new_entities = False
    entry.pref_disable_polling = False
    entry.data = {
        "host": "192.168.1.101",
        "port": 80,
    }
    entry.options = {}
    entry.runtime_data = None

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["entry"]["entry_id"] == "test_entry_no_coord"
    assert diagnostics["entry"]["data"]["host"] == "**REDACTED**"
    assert diagnostics["coordinator"] == {}
