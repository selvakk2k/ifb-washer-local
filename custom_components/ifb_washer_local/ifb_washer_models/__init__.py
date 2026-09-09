"""IFB Washer Models: Hardware Profiles & Capability Gating for IFB Smart Washing Machines."""

from .const import (
    HIL_OPTION_ANTI_CREASE,
    HIL_OPTION_AROMA,
    HIL_OPTION_DRY,
    HIL_OPTION_ECO,
    HIL_OPTION_EXTRA_RINSE,
    HIL_OPTION_HOT_RINSE,
    HIL_OPTION_PRE_WASH,
    HIL_OPTION_RAPID_WASH,
    HIL_OPTION_RINSE_HOLD,
    HIL_OPTION_STEAM,
    HIL_OPTION_TIME_SAVER,
    HIL_OPTION_WARM_SOAK,
    ApplianceArchetype,
    ManualInfo,
    ModelInfo,
    ProgramCapabilities,
)
from .lookup import WasherModelLookup, get_lookup

__version__ = "0.1.0"

__all__ = [
    "WasherModelLookup",
    "get_lookup",
    "ModelInfo",

    "ManualInfo",
    "ProgramCapabilities",
    "ApplianceArchetype",
    "HIL_OPTION_RAPID_WASH",
    "HIL_OPTION_PRE_WASH",
    "HIL_OPTION_EXTRA_RINSE",
    "HIL_OPTION_RINSE_HOLD",
    "HIL_OPTION_HOT_RINSE",
    "HIL_OPTION_TIME_SAVER",
    "HIL_OPTION_ECO",
    "HIL_OPTION_ANTI_CREASE",
    "HIL_OPTION_DRY",
    "HIL_OPTION_STEAM",
    "HIL_OPTION_AROMA",
    "HIL_OPTION_WARM_SOAK",
]
