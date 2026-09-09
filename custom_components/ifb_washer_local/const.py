"""Constants for the IFB Washer Local Home Assistant integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "ifb_washer_local"

# Configuration keys
CONF_HOST = "host"
CONF_PORT = "port"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_FAMILY = "family"
CONF_MODEL = "model"
CONF_CUSTOM_MODEL = "custom_model"
CONF_CUSTOM_PROGRAMS = "custom_programs"

DEFAULT_PORT = 80
DEFAULT_FAMILY = "washer_dryer"
DEFAULT_SCAN_INTERVAL_STANDBY = 15
DEFAULT_SCAN_INTERVAL_RUNNING = 5

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.BUTTON,
    Platform.SWITCH,
]

