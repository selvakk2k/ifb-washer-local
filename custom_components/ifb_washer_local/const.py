"""Constants for the IFB Washer Local Home Assistant integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "ifb_washer_local"

# Configuration keys
CONF_HOST = "host"
CONF_PORT = "port"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_PORT = 80
DEFAULT_SCAN_INTERVAL_STANDBY = 15
DEFAULT_SCAN_INTERVAL_RUNNING = 5

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.BUTTON,
    Platform.SWITCH,
]
