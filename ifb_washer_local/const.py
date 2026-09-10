"""Constants and protocol mappings for the IFB Washer Local integration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum, IntEnum

DEFAULT_PORT = 80
GAINSPAN_PROFILE_ENDPOINT = "/gainspan/profile/ifb"

# Command Header and Types
FRAME_HEADER = 0x63

CMD_TYPE_FIXED = 0x01
CMD_TYPE_USER_OPTION = 0x02
CMD_TYPE_PROGRAM_SELECT = 0x03

# Fixed Machine Commands (Type 0x01)
FIXED_CMD_PLAY = 0x01
FIXED_CMD_PAUSE = 0x03
FIXED_CMD_CANCEL = 0x04
FIXED_CMD_STATUS_QUERY = 0x07
FIXED_CMD_POWER_ON = 0x11
FIXED_CMD_POWER_OFF = 0x12

# Hardware Interface Layer (HIL) Option Identifiers (Type 0x02)
HIL_OPTION_TEMP = 3
HIL_OPTION_RAPID_WASH = 4
HIL_OPTION_SPIN = 5
HIL_OPTION_PRE_WASH = 6
HIL_OPTION_EXTRA_RINSE = 7
HIL_OPTION_RINSE_HOLD = 8
HIL_OPTION_DELAY = 9
HIL_OPTION_SOAK = 10
HIL_OPTION_CHILD_LOCK = 11
HIL_OPTION_HOT_RINSE = 12
HIL_OPTION_TIME_SAVER = 13
HIL_OPTION_ECO = 14
HIL_OPTION_SOIL_AGE = 15
HIL_OPTION_ANTI_CREASE = 16
HIL_OPTION_DRY = 18
HIL_OPTION_STEAM = 19
HIL_OPTION_AROMA = 21
HIL_OPTION_WARM_SOAK = 22


class MachineState(IntEnum):
    """Operational machine cycle states reported by the washer MCU."""

    IDLE = 0
    STANDBY = 1
    STARTING = 2
    PRE_WASH = 3
    MAIN_WASH = 4
    EXTRA_RINSE_1 = 5
    EXTRA_RINSE_2 = 6
    EXTRA_RINSE_3 = 7
    FIRST_RINSE = 8
    SECOND_RINSE = 9
    FINAL_RINSE = 10
    FINAL_SPIN = 11
    ANTI_CREASE = 12
    COMPLETE = 13
    PAUSED = 14
    SOAK = 15
    RINSE_HOLD = 16
    HEATING = 17
    DRAINING = 18
    INTERMEDIATE_SPIN = 19
    DELAY_START = 20
    COOLING = 22
    HOT_RINSE_START = 35
    STEAM = 36
    RINSE_HOLD_CHILD_LOCK = 39
    DRY = 40
    CHILD_LOCK_END = 50
    SYNCING_65 = 65
    SYNCING_118 = 118


STATE_LABELS: dict[int, str] = {
    MachineState.IDLE: "Idle",
    MachineState.STANDBY: "Standby",
    MachineState.STARTING: "Starting",
    MachineState.PRE_WASH: "Pre-wash",
    MachineState.MAIN_WASH: "Main Wash",
    MachineState.EXTRA_RINSE_1: "Extra Rinse 1",
    MachineState.EXTRA_RINSE_2: "Extra Rinse 2",
    MachineState.EXTRA_RINSE_3: "Extra Rinse 3",
    MachineState.FIRST_RINSE: "First Rinse",
    MachineState.SECOND_RINSE: "Second Rinse",
    MachineState.FINAL_RINSE: "Final Rinse",
    MachineState.FINAL_SPIN: "Final Spin",
    MachineState.ANTI_CREASE: "Anti-crease",
    MachineState.COMPLETE: "Complete",
    MachineState.PAUSED: "Paused",
    MachineState.SOAK: "Soak",
    MachineState.RINSE_HOLD: "Rinse Hold",
    MachineState.HEATING: "Heating",
    MachineState.DRAINING: "Draining",
    MachineState.INTERMEDIATE_SPIN: "Intermediate Spin",
    MachineState.DELAY_START: "Delay Start",
    MachineState.COOLING: "Cooling",
    MachineState.HOT_RINSE_START: "Hot Rinse Start",
    MachineState.STEAM: "Steam",
    MachineState.RINSE_HOLD_CHILD_LOCK: "Rinse Hold (Child Lock)",
    MachineState.DRY: "Dry",
    MachineState.CHILD_LOCK_END: "Child Lock End",
    MachineState.SYNCING_65: "Syncing",
    MachineState.SYNCING_118: "Syncing",
}

# Door States
DOOR_STATE_UNLOCKED = 1
DOOR_STATE_LOCKED = 2
DOOR_STATE_LOCKING = 3
DOOR_STATE_UNLOCKING = 4
DOOR_STATE_CLOSED_OR_LOCKED = DOOR_STATE_UNLOCKED


class ApplianceFamily(str, Enum):
    """Supported appliance families."""

    WASHER_DRYER = "washer_dryer"
    FRONT_LOAD = "front_load"
    TOP_LOAD_SMART = "top_load_smart"
    CUSTOM = "custom"
    AUTO_DETECT = "auto_detect"


# Verified Program Codes for IFB Washer Dryer 742 Series (WD Executive ZXS)
# Hardware verified by 14-position physical clockwise dial rotation:
PROGRAM_CODES_WASHER_DRYER: dict[int, str] = {
    1: "Wash + Dry 2Hr",
    2: "Wash + Dry 4Hr",
    3: "Steam & Dry",
    4: "Refresh",
    5: "Power Steam",
    6: "CradleWash®",
    7: "Wool",
    8: "Bulky",
    9: "Baby Wear",
    10: "Anti-Allergen",
    11: "Synthetic",
    12: "Cotton",
    13: "Mix / Daily",
    14: "Express 15'",
    15: "Tub Clean",
}

# Alias for backwards compatibility
PROGRAM_CODES_742 = PROGRAM_CODES_WASHER_DRYER

# Front Load Series (Senator / Executive Plus Series - from manual FL_790_G)
PROGRAM_CODES_FRONT_LOAD: dict[int, str] = {
    1: "Mix / Daily",
    2: "Cotton",
    3: "Uniform / Linen",
    4: "Baby Wear",
    5: "Anti-Allergen",
    6: "Express 30'",
    7: "Express 15'",
    8: "Refresh",
    9: "Wool",
    10: "Synthetic",
    11: "CradleWash®",
    12: "Bulky / Bedding",
    13: "Sports Wear",
    14: "Dark Wash",
    15: "Jeans",
    16: "PowerSteam®",
    17: "Inner Wear",
    18: "Shirts",
    19: "Tub Clean",
    20: "Spin Dry / Rinse",
}

# Smart Top Load Series (SWID / SID Series - from manual TL_360_UM)
PROGRAM_CODES_TOP_LOAD: dict[int, str] = {
    1: "Mix / Daily",
    2: "Cotton",
    3: "Express 30'",
    4: "Synthetic",
    5: "Delicates",
    6: "StainFighter™",
    7: "Bulky",
    8: "Anti-Allergen",
    9: "Rinse + Spin",
    10: "Tub Clean",
    11: "Saree",
    12: "Baby Wear",
    13: "Uniform",
    14: "Jeans",
    15: "Sports Wear",
}

FAMILY_PROGRAM_MATRICES: dict[str, dict[int, str]] = {
    ApplianceFamily.WASHER_DRYER: PROGRAM_CODES_WASHER_DRYER,
    ApplianceFamily.FRONT_LOAD: PROGRAM_CODES_FRONT_LOAD,
    ApplianceFamily.TOP_LOAD_SMART: PROGRAM_CODES_TOP_LOAD,
}

# Human-friendly IFB Terminology for Machine Types
MACHINE_TYPE_LABELS: dict[str, str] = {
    ApplianceFamily.WASHER_DRYER: "Washer Dryer Refresher",
    ApplianceFamily.FRONT_LOAD: "Front Load Washer",
    ApplianceFamily.TOP_LOAD_SMART: "Top Load Washer",
}

# Known Models Catalog per Appliance Category
MODELS_BY_FAMILY: dict[str, list[str]] = {
    ApplianceFamily.WASHER_DRYER: [
        "WD Executive ZXS",
        "WD Executive ZXR",
        "TurboDry 7010",
        "TurboDry 8514",
        "Senator WDR",
        "Senator Smart Touch WDR",
        "Washer Dryer 742 Series",
        "custom",
    ],
    ApplianceFamily.FRONT_LOAD: [
        "Executive ZXM / Plus",
        "Senator Smart Touch",
        "Senator Neo / Plus",
        "Elite MXS / Plus",
        "Serena ZSS / MSS",
        "Senorita SXS / VXS",
        "Elena Plus / Eva Plus",
        "Diva Aqua",
        "custom",
    ],
    ApplianceFamily.TOP_LOAD_SMART: [
        "TL-RGS Aqua",
        "TL-R2BSS / R2BR",
        "TL801 / TL800",
        "Smart Top Load (SWID / SID Series)",
        "custom",
    ],
}

# Physical Dial Sides Mapping (Left vs Right Arcs / Groups)
# For front load and washer dryers: (right_side_codes, left_side_codes)
# For top loaders: (group1_daily_codes, group2_special_codes)
DIAL_SIDES_BY_FAMILY: dict[str, tuple[list[int], list[int]]] = {
    ApplianceFamily.WASHER_DRYER: (
        [1, 2, 3, 4, 5, 6, 7],
        [8, 9, 10, 11, 12, 13, 14, 15],
    ),
    ApplianceFamily.FRONT_LOAD: (
        [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
        [1, 2, 3, 4, 5, 6, 7],
    ),
    ApplianceFamily.TOP_LOAD_SMART: (
        [1, 2, 3, 4, 5],
        [6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
    ),
}


# Telemetry Signature Definition & Lookup Table for Reverse-Engineering Programs
from dataclasses import dataclass


@dataclass(frozen=True)
class ProgramSignature:
    """Telemetry signature tuple for program auto-detection."""

    name: str
    duration_min: int
    temp_c: int
    spin_rpm: int
    is_dry_enabled: bool = False


TELEMETRY_SIGNATURES: tuple[ProgramSignature, ...] = (
    ProgramSignature("Express 15'", 15, 0, 800, False),
    ProgramSignature("Refresh", 30, 0, 0, False),
    ProgramSignature("CradleWash®", 37, 30, 400, False),
    ProgramSignature("Wool", 43, 30, 800, False),
    ProgramSignature("Mix / Daily", 72, 40, 1000, False),
    ProgramSignature("Anti-Allergen", 115, 60, 1000, False),
    ProgramSignature("Cotton", 163, 60, 1400, False),
    ProgramSignature("Wash + Dry 2Hr", 120, 40, 1000, True),
    ProgramSignature("Wash + Dry 4Hr", 240, 40, 1200, True),
)

# Common Telemetry Fault Codes (from official IFB manufacturer catalog)
ERROR_CODES: dict[int, tuple[str, str]] = {
    0: ("", "No Error"),
    1: ("door", "Door Error"),
    2: ("prs", "Pressure Switch Failure"),
    3: ("oht", "Over Heat"),
    4: ("ofl", "Water Overflow"),
    5: ("mot", "Motor Failure"),
    6: ("hot", "Hot (High Drum Temp)"),
    7: ("tri", "Triac Short"),
    8: ("unb", "Unbalance Error"),
    9: ("hvt", "High Voltage"),
    10: ("lvt", "Low Voltage"),
    11: ("drn", "Drain Pump Failure"),
    12: ("tsn", "Temperature Sensor Error"),
    13: ("htr", "Heating Error"),
    14: ("tAP", "No Water / Low Water Pressure"),
    15: ("tAP", "No Water / Low Water Pressure"),
    16: ("dht", "Clothes Not Drying - Dryer Heater Fault"),
    17: ("wfi", "Wi-Fi Communication Error"),
    18: ("pwr", "Power Board Communication Error"),
    19: ("ipm", "IPM Overheat"),
    20: ("moc", "Motor Over Current"),
    21: ("dfn", "Dryer Fan Fault"),
    22: ("dsn", "Clothes Not Drying - Dryer Sensor Fault"),
    23: ("bkr", "Blocked Rotor"),
    24: ("unk", "Unknown Error"),
    25: ("sft", "Softener Low"),
    26: ("dtg", "Detergent Low"),
    27: ("ddt", "DD Tray Not Closed"),
    28: ("ad1", "Detergent Dispensing Pump Error (AD1)"),
    29: ("ad2", "Softener Dispensing Pump Error (AD2)"),
    30: ("dsf", "Clothes Not Drying - Drying Sensor Fault"),
}

# Spin Speed Options (Option ID 5)
SPIN_SPEED_OPTIONS: dict[int, str] = {
    0: "No Spin",
    1: "400 RPM",
    2: "600 RPM",
    4: "800 RPM",
    6: "1000 RPM",
    7: "1200 RPM",
    8: "1400 RPM",
}

SPIN_SPEED_RPM_TO_CODE: dict[int, int] = {
    0: 0,
    400: 1,
    600: 2,
    800: 4,
    1000: 6,
    1200: 7,
    1400: 8,
}

SPIN_SPEED_CODE_TO_RPM: dict[int, int] = {
    code: rpm for rpm, code in SPIN_SPEED_RPM_TO_CODE.items()
}

# Temperature Options (Option ID 3)
TEMPERATURE_OPTIONS: dict[int, str] = {
    0: "None",
    2: "Cold",
    3: "30°C",
    4: "40°C",
    5: "60°C",
    6: "95°C",
    7: "20°C",
    8: "40°C Eco",
    9: "60°C Eco",
}

TEMPERATURE_CELSIUS_TO_CODE: dict[int, int] = {
    0: 2,
    20: 7,
    30: 3,
    40: 4,
    60: 5,
    95: 6,
}

TEMPERATURE_CODE_TO_CELSIUS: dict[int, int] = {
    2: 0,
    7: 20,
    3: 30,
    4: 40,
    5: 60,
    6: 95,
    8: 40,
    9: 60,
}

# Delay Start Options (Option ID 9) - Capped at 19 Hours per IFB appliance specification
# Hardware command values: 0 = No Delay, 1 = 30 Minutes, 2 = 1 Hour, 4 = 2 Hours ... 38 = 19 Hours
DELAY_START_OPTIONS: dict[int, str] = {
    0: "No Delay",
    1: "30 Minutes",
    **{h * 2: f"{h} Hour" if h == 1 else f"{h} Hours" for h in range(1, 20)},
}

DELAY_START_NAME_TO_CODE: dict[str, int] = {
    name: code for code, name in DELAY_START_OPTIONS.items()
}

# Extra Rinse Options (Option ID 7)
# Hardware command values: 0 = 0 (None), 1 = +1 Rinse, 2 = +2 Rinses, 3 = +3 Rinses
EXTRA_RINSE_OPTIONS: dict[int, str] = {
    0: "0 (None)",
    1: "+1 Rinse",
    2: "+2 Rinses",
    3: "+3 Rinses",
}

EXTRA_RINSE_NAME_TO_CODE: dict[str, int] = {
    name: code for code, name in EXTRA_RINSE_OPTIONS.items()
}

# Dry Mode Options (Option ID 18)
# Hardware command values from IFB Washer Dryer catalog
DRY_OPTIONS: dict[int, str] = {
    0: "No Dry",
    1: "Cupboard Dry",
    2: "Iron Dry",
    3: "Eco Dry",
    4: "Gentle Dry",
    5: "Time Dry",
    6: "Cradle Dry",
    7: "30 Minutes",
    8: "1 Hour",
    9: "1 Hour 30 Minutes",
    10: "2 Hours",
    11: "2 Hours 30 Minutes",
    12: "3 Hours",
    13: "3 Hours 30 Minutes",
    14: "4 Hours",
    15: "4 Hours 30 Minutes",
    16: "5 Hours",
    17: "6 Hours",
}

DRY_NAME_TO_CODE: dict[str, int] = {
    name: code for code, name in DRY_OPTIONS.items()
}
# Backward compatibility alias
DRY_NAME_TO_CODE["Off"] = 0


@dataclass(frozen=True)
class ProgramCapabilities:
    """Operational boundaries and supported options for a specific wash program."""

    program_name: str = ""
    allowed_temps: tuple[str, ...] = ("Cold", "20°C", "30°C", "40°C", "60°C", "95°C")
    allowed_spins: tuple[str, ...] = (
        "No Spin",
        "400 RPM",
        "600 RPM",
        "800 RPM",
        "1000 RPM",
        "1200 RPM",
        "1400 RPM",
    )
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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProgramCapabilities:
        """Create ProgramCapabilities instance from a dictionary."""
        return cls(
            program_name=str(data.get("program_name", "")),
            allowed_temps=tuple(data.get("allowed_temps", ())),
            allowed_spins=tuple(data.get("allowed_spins", ())),
            supports_dry=bool(data.get("supports_dry", False)),
            allowed_dry_modes=tuple(data.get("allowed_dry_modes", ("No Dry",))),
            max_dry_time_min=int(data.get("max_dry_time_min", 0)),
            supports_steam=bool(data.get("supports_steam", False)),
            steam_behavior=str(data.get("steam_behavior", "none")),
            supports_prewash=bool(data.get("supports_prewash", False)),
            supports_soak=bool(data.get("supports_soak", False)),
            supports_time_saver=bool(data.get("supports_time_saver", False)),
            supports_extra_rinse=bool(data.get("supports_extra_rinse", True)),
            max_extra_rinses=int(data.get("max_extra_rinses", 3)),
            supports_hot_rinse=bool(data.get("supports_hot_rinse", False)),
            requires_extra_rinse_for_hot_rinse=bool(
                data.get("requires_extra_rinse_for_hot_rinse", True)
            ),
            supports_rinse_hold=bool(data.get("supports_rinse_hold", True)),
            supports_eco=bool(data.get("supports_eco", False)),
            supports_aroma=bool(data.get("supports_aroma", False)),
            supports_anti_crease=bool(data.get("supports_anti_crease", False)),
            supports_delay_start=bool(data.get("supports_delay_start", True)),
        )


# Program Capabilities per Official Wash Guide Map (Pages 57-67)
PROGRAM_CAPABILITIES_WASHER_DRYER: dict[int, ProgramCapabilities] = {
    1: ProgramCapabilities(
        allowed_temps=("Cold", "30°C", "40°C"),
        allowed_spins=("400 RPM", "600 RPM", "800 RPM", "1000 RPM", "1200 RPM"),
        supports_dry=True,
        allowed_dry_modes=("No Dry", "Cupboard Dry", "Iron Dry", "Eco Dry", "30 Minutes", "1 Hour", "1 Hour 30 Minutes", "2 Hours"),
        supports_steam=False,
        supports_prewash=False,
        supports_soak=False,
    ),
    2: ProgramCapabilities(
        allowed_temps=("Cold", "30°C", "40°C"),
        allowed_spins=("400 RPM", "600 RPM", "800 RPM", "1000 RPM", "1200 RPM", "1400 RPM"),
        supports_dry=True,
        allowed_dry_modes=("No Dry", "Cupboard Dry", "Iron Dry", "Eco Dry", "30 Minutes", "1 Hour", "1 Hour 30 Minutes", "2 Hours", "2 Hours 30 Minutes", "3 Hours", "3 Hours 30 Minutes", "4 Hours", "4 Hours 30 Minutes", "5 Hours", "6 Hours"),
    ),
    3: ProgramCapabilities(
        allowed_temps=("Cold", "30°C", "40°C", "60°C", "95°C"),
        allowed_spins=("400 RPM", "600 RPM", "800 RPM", "1000 RPM", "1200 RPM", "1400 RPM"),
        supports_dry=True,
        allowed_dry_modes=("No Dry", "Cupboard Dry", "Iron Dry", "Eco Dry", "30 Minutes", "1 Hour", "1 Hour 30 Minutes", "2 Hours", "2 Hours 30 Minutes", "3 Hours", "3 Hours 30 Minutes", "4 Hours"),
    ),
    4: ProgramCapabilities(
        allowed_temps=("Cold",),
        allowed_spins=("No Spin",),
        supports_dry=False,
        allowed_dry_modes=("No Dry",),
        supports_steam=True,
        supports_prewash=False,
        supports_soak=False,
        supports_extra_rinse=False,
        supports_hot_rinse=False,
        supports_rinse_hold=False,
        supports_eco=False,
    ),
    5: ProgramCapabilities(
        allowed_temps=("Cold", "30°C", "40°C", "60°C"),
        allowed_spins=("400 RPM", "600 RPM", "800 RPM"),
        supports_dry=False,
        allowed_dry_modes=("No Dry",),
        supports_prewash=False,
        supports_soak=False,
        supports_time_saver=False,
    ),
    6: ProgramCapabilities(
        allowed_temps=("Cold", "30°C", "40°C"),
        allowed_spins=("No Spin", "400 RPM", "600 RPM"),
        supports_dry=True,
        allowed_dry_modes=("No Dry", "Cradle Dry", "Gentle Dry", "30 Minutes", "1 Hour"),
        supports_steam=False,
        supports_prewash=False,
        supports_soak=False,
        supports_time_saver=False,
    ),
    7: ProgramCapabilities(
        allowed_temps=("Cold", "30°C", "40°C"),
        allowed_spins=("400 RPM", "600 RPM", "800 RPM", "1000 RPM", "1200 RPM"),
        supports_dry=True,
        allowed_dry_modes=("No Dry", "Gentle Dry", "30 Minutes", "1 Hour", "1 Hour 30 Minutes", "2 Hours"),
        supports_steam=False,
        supports_prewash=False,
        supports_soak=False,
    ),
    8: ProgramCapabilities(
        allowed_temps=("Cold", "30°C", "40°C", "60°C"),
        allowed_spins=("400 RPM", "600 RPM", "800 RPM", "1000 RPM"),
        supports_dry=True,
        allowed_dry_modes=("No Dry", "Cupboard Dry", "Iron Dry", "1 Hour", "2 Hours", "3 Hours"),
        supports_prewash=False,
        supports_time_saver=False,
    ),
    9: ProgramCapabilities(
        allowed_temps=("40°C", "60°C", "95°C"),
        allowed_spins=("No Spin", "400 RPM", "600 RPM", "800 RPM", "1000 RPM", "1200 RPM", "1400 RPM"),
        supports_dry=True,
        allowed_dry_modes=("No Dry", "Cupboard Dry", "Iron Dry", "1 Hour", "2 Hours", "3 Hours"),
        supports_time_saver=False,
    ),
    10: ProgramCapabilities(
        allowed_temps=("40°C", "60°C", "95°C"),
        allowed_spins=("No Spin", "400 RPM", "600 RPM", "800 RPM", "1000 RPM", "1200 RPM", "1400 RPM"),
        supports_dry=True,
        allowed_dry_modes=("No Dry", "Cupboard Dry", "Iron Dry", "1 Hour", "2 Hours", "3 Hours"),
        supports_steam=True,
    ),
    11: ProgramCapabilities(
        allowed_temps=("Cold", "30°C", "40°C", "60°C"),
        allowed_spins=("No Spin", "400 RPM", "600 RPM", "800 RPM", "1000 RPM", "1200 RPM"),
        supports_dry=True,
        allowed_dry_modes=("No Dry", "Cupboard Dry", "Iron Dry", "Gentle Dry", "30 Minutes", "1 Hour", "1 Hour 30 Minutes", "2 Hours", "2 Hours 30 Minutes", "3 Hours"),
    ),
    12: ProgramCapabilities(
        allowed_temps=("Cold", "30°C", "40°C", "60°C", "95°C"),
        allowed_spins=("No Spin", "400 RPM", "600 RPM", "800 RPM", "1000 RPM", "1200 RPM", "1400 RPM"),
        supports_dry=True,
        allowed_dry_modes=("No Dry", "Cupboard Dry", "Iron Dry", "Eco Dry", "30 Minutes", "1 Hour", "1 Hour 30 Minutes", "2 Hours", "2 Hours 30 Minutes", "3 Hours", "3 Hours 30 Minutes", "4 Hours"),
    ),
    13: ProgramCapabilities(
        allowed_temps=("Cold", "20°C", "30°C", "40°C", "60°C"),
        allowed_spins=("No Spin", "400 RPM", "600 RPM", "800 RPM", "1000 RPM", "1200 RPM"),
        supports_dry=True,
        allowed_dry_modes=("No Dry", "Cupboard Dry", "Iron Dry", "Eco Dry", "30 Minutes", "1 Hour", "1 Hour 30 Minutes", "2 Hours", "2 Hours 30 Minutes", "3 Hours"),
    ),
    14: ProgramCapabilities(
        allowed_temps=("Cold", "30°C", "40°C"),
        allowed_spins=("No Spin", "400 RPM", "600 RPM", "800 RPM", "1000 RPM", "1200 RPM"),
        supports_dry=False,
        allowed_dry_modes=("No Dry",),
        supports_prewash=False,
        supports_soak=False,
        supports_time_saver=False,
    ),
    15: ProgramCapabilities(
        allowed_temps=("Cold", "60°C", "95°C"),
        allowed_spins=("No Spin", "400 RPM", "600 RPM", "800 RPM"),
        supports_dry=False,
        allowed_dry_modes=("No Dry",),
        supports_steam=False,
        supports_prewash=False,
        supports_soak=False,
        supports_time_saver=False,
        supports_extra_rinse=False,
        supports_hot_rinse=False,
        supports_rinse_hold=False,
        supports_eco=False,
        supports_aroma=False,
        supports_anti_crease=False,
    ),
    16: ProgramCapabilities(
        allowed_temps=("Cold",),
        allowed_spins=("No Spin", "400 RPM", "600 RPM", "800 RPM", "1000 RPM", "1200 RPM", "1400 RPM"),
        supports_dry=False,
        allowed_dry_modes=("No Dry",),
        supports_steam=False,
        supports_prewash=False,
        supports_soak=False,
        supports_time_saver=False,
        supports_extra_rinse=False,
        supports_hot_rinse=False,
        supports_rinse_hold=False,
        supports_eco=False,
        supports_aroma=False,
        supports_anti_crease=True,
    ),
    17: ProgramCapabilities(
        allowed_temps=("Cold",),
        allowed_spins=("No Spin", "400 RPM", "600 RPM", "800 RPM", "1000 RPM", "1200 RPM", "1400 RPM"),
        supports_dry=False,
        allowed_dry_modes=("No Dry",),
        supports_steam=False,
        supports_prewash=False,
        supports_soak=False,
        supports_time_saver=False,
        supports_extra_rinse=True,
        supports_hot_rinse=False,
        supports_rinse_hold=True,
        supports_eco=False,
        supports_aroma=True,
        supports_anti_crease=True,
    ),
}

DEFAULT_PROGRAM_CAPABILITIES = ProgramCapabilities(
    allowed_temps=("Cold", "30°C", "40°C", "60°C", "95°C"),
    allowed_spins=("No Spin", "400 RPM", "600 RPM", "800 RPM", "1000 RPM", "1200 RPM", "1400 RPM"),
    supports_dry=True,
    allowed_dry_modes=tuple(DRY_OPTIONS.values()),
    supports_steam=True,
    supports_prewash=True,
    supports_soak=True,
    supports_time_saver=True,
    supports_extra_rinse=True,
    supports_hot_rinse=True,
    supports_rinse_hold=True,
    supports_eco=True,
    supports_aroma=True,
    supports_anti_crease=True,
)


PROGRAM_CAPABILITIES_FRONT_LOAD: dict[int, ProgramCapabilities] = PROGRAM_CAPABILITIES_WASHER_DRYER
PROGRAM_CAPABILITIES_TOP_LOAD: dict[int, ProgramCapabilities] = PROGRAM_CAPABILITIES_WASHER_DRYER


def get_program_capabilities(program_code: int) -> ProgramCapabilities:
    """Return program option capabilities for a given program code."""
    return PROGRAM_CAPABILITIES_WASHER_DRYER.get(program_code, DEFAULT_PROGRAM_CAPABILITIES)



