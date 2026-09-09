"""Constants, dataclasses, and enums for IFB Washer Models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ApplianceArchetype(str, Enum):
    """Physical appliance interface archetypes."""

    WASHER_DRYER_REFRESHER = "Washer-Dryer Refresher"
    FRONT_LOAD_SMART_ROTARY = "Front Load Smart Rotary"
    FRONT_LOAD_TOUCH_STEPPER = "Front Load Touch/Stepper"
    TOP_LOAD_SMART_WIFI = "Top Load Smart Wi-Fi"


@dataclass(frozen=True)
class ModelInfo:
    """Commercial model metadata."""

    id: int
    manual_code: str
    model_name: str
    series: str
    finish_code: str
    capacity_kg: float
    spin_max_rpm: int
    archetype: ApplianceArchetype | str


@dataclass(frozen=True)
class ManualInfo:
    """Audited manual and fascia diagram metadata."""

    id: int
    manual_code: str
    file_name: str
    archetype: ApplianceArchetype | str
    model_series: str
    page_count: int
    panel_page: int
    prog_table_page: int
    panel_image_path: str


@dataclass(frozen=True)
class ProgramCapabilities:
    """Operational boundaries and supported options for a specific wash program."""

    program_name: str
    allowed_temps: tuple[str, ...] = ("Cold", "30°C", "40°C", "60°C", "95°C")
    allowed_spins: tuple[str, ...] = ("No Spin", "400 RPM", "600 RPM", "800 RPM", "1000 RPM", "1200 RPM", "1400 RPM")
    supports_dry: bool = False
    allowed_dry_modes: tuple[str, ...] = ("No Dry",)
    max_dry_time_min: int = 0
    supports_steam: bool = False
    steam_behavior: str = "none"  # "none", "optional", "mandatory"
    supports_prewash: bool = False
    supports_soak: bool = False
    supports_time_saver: bool = False
    supports_extra_rinse: bool = True
    max_extra_rinses: int = 3
    supports_hot_rinse: bool = False
    requires_extra_rinse_for_hot_rinse: bool = True
    supports_rinse_hold: bool = True
    supports_eco: bool = False
    supports_aroma: bool = False
    supports_anti_crease: bool = False
    supports_delay_start: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert capabilities to dictionary format."""
        return {
            "program_name": self.program_name,
            "allowed_temps": list(self.allowed_temps),
            "allowed_spins": list(self.allowed_spins),
            "supports_dry": self.supports_dry,
            "allowed_dry_modes": list(self.allowed_dry_modes),
            "max_dry_time_min": self.max_dry_time_min,
            "supports_steam": self.supports_steam,
            "steam_behavior": self.steam_behavior,
            "supports_prewash": self.supports_prewash,
            "supports_soak": self.supports_soak,
            "supports_time_saver": self.supports_time_saver,
            "supports_extra_rinse": self.supports_extra_rinse,
            "max_extra_rinses": self.max_extra_rinses,
            "supports_hot_rinse": self.supports_hot_rinse,
            "requires_extra_rinse_for_hot_rinse": self.requires_extra_rinse_for_hot_rinse,
            "supports_rinse_hold": self.supports_rinse_hold,
            "supports_eco": self.supports_eco,
            "supports_aroma": self.supports_aroma,
            "supports_anti_crease": self.supports_anti_crease,
            "supports_delay_start": self.supports_delay_start,
        }


# Hardware Option IDs (GainSpan 9-byte option packet command type 0x02)
HIL_OPTION_RAPID_WASH = 4
HIL_OPTION_PRE_WASH = 6
HIL_OPTION_EXTRA_RINSE = 7
HIL_OPTION_RINSE_HOLD = 8
HIL_OPTION_HOT_RINSE = 12
HIL_OPTION_TIME_SAVER = 13
HIL_OPTION_ECO = 14
HIL_OPTION_ANTI_CREASE = 16
HIL_OPTION_DRY = 18
HIL_OPTION_STEAM = 19
HIL_OPTION_AROMA = 21
HIL_OPTION_WARM_SOAK = 22
