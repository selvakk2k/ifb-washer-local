"""Constants and protocol mappings for the IFB Washer Local integration."""

from __future__ import annotations

from enum import IntEnum

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
FIXED_CMD_POWER_OFF = 0x12

# Hardware Interface Layer (HIL) Option Identifiers (Type 0x02)
HIL_OPTION_TEMP = 3
HIL_OPTION_SPIN = 5
HIL_OPTION_EXTRA_RINSE = 7
HIL_OPTION_DELAY = 9
HIL_OPTION_SOAK = 10
HIL_OPTION_CHILD_LOCK = 11


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
DOOR_STATE_CLOSED_OR_LOCKED = 1
DOOR_STATE_LOCKED = 2
DOOR_STATE_LOCKING = 3
DOOR_STATE_UNLOCKING = 4

# Verified Program Codes for IFB Washer Dryer 742 Series
# Hardware verified: Program 12 = Cotton, Program 13 = Mix / Daily, Program 14 = Tub Clean
PROGRAM_CODES_742: dict[int, str] = {
    1: "Synthetic",
    2: "Baby Wear",
    3: "Express 15'",
    4: "Bulky Beddings",
    5: "CradleWash",
    6: "Rinse + Spin",
    7: "Wool",
    8: "Sports Wear",
    9: "Wash + Dry 4Hr",
    10: "Wash + Dry 2Hr",
    11: "Steam & Dry",
    12: "Cotton",
    13: "Mix / Daily",
    14: "Tub Clean",
    15: "Refresh",
    16: "PowerSteam",
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

# Temperature Options (Option ID 3)
TEMPERATURE_OPTIONS: dict[int, str] = {
    0: "Not Set",
    2: "Cold",
    3: "30°C",
    4: "40°C",
    5: "60°C",
    6: "95°C",
    8: "40°C Eco",
    9: "60°C Eco",
}

TEMPERATURE_CELSIUS_TO_CODE: dict[int, int] = {
    0: 2,
    20: 2,
    30: 3,
    40: 4,
    60: 5,
    95: 6,
}
