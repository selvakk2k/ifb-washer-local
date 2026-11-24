"""Pytest configuration and Home Assistant stubs for IFB Washer Local."""

import sys
from pathlib import Path

# Add project root and custom_components to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Set up Home Assistant mock stubs for standalone testing
from tests.ha_stub import setup_ha_stubs  # noqa: E402

setup_ha_stubs()

