"""Automated hardware capability profiler for IFB front-load washing machines and washer dryers."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Optional

from .client import IFBWasherClient
from .const import (
    DRY_OPTIONS,
    EXTRA_RINSE_OPTIONS,
    HIL_OPTION_DRY,
    HIL_OPTION_EXTRA_RINSE,
    HIL_OPTION_SPIN,
    HIL_OPTION_TEMP,
    PROGRAM_CAPABILITIES_FRONT_LOAD,
    PROGRAM_CAPABILITIES_TOP_LOAD,
    PROGRAM_CAPABILITIES_WASHER_DRYER,
    SPIN_SPEED_OPTIONS,
    TEMPERATURE_OPTIONS,
    ProgramCapabilities,
    get_program_capabilities,
)
from .protocol import build_user_option_command

_LOGGER = logging.getLogger(__name__)

# Standard candidate probe values
CANDIDATE_SPIN_CODES = [0, 1, 2, 4, 6, 7, 8]  # No Spin, 400, 600, 800, 1000, 1200, 1400
CANDIDATE_TEMP_CODES = [2, 7, 3, 4, 5, 6]     # Cold, 20°C, 30°C, 40°C, 60°C, 95°C
CANDIDATE_EXTRA_RINSES = [0, 1, 2, 3]
CANDIDATE_DRY_CODES = [0, 1, 2, 7, 8, 9, 10]   # No Dry, Cupboard, Iron, 30m, 1h, 1.5h, 2h

SPIN_NAME_TO_CODE = {name: code for code, name in SPIN_SPEED_OPTIONS.items()}
TEMP_NAME_TO_CODE = {name: code for code, name in TEMPERATURE_OPTIONS.items()}


async def probe_single_program(
    client: IFBWasherClient,
    program_code: int,
    base_caps: Optional[ProgramCapabilities] = None,
    is_washer_dryer: bool = True,
    delay_between_cmds: float = 0.35,
    candidate_spins: Optional[list[int]] = None,
    candidate_temps: Optional[list[int]] = None,
) -> ProgramCapabilities:
    """Probe a single wash program for exact hardware spin ceilings, temperature acceptance, and options."""
    if base_caps is None:
        base_caps = get_program_capabilities(program_code)

    _LOGGER.debug("Probing program code %d on washer...", program_code)
    try:
        await client.select_program(program_code)
        await asyncio.sleep(delay_between_cmds * 2)
    except Exception as exc:
        _LOGGER.warning("Could not select program %d during calibration: %s", program_code, exc)
        return base_caps

    # 1. Probe Spin Speeds
    allowed_spins: list[str] = []
    spins_to_test = candidate_spins if candidate_spins is not None else CANDIDATE_SPIN_CODES
    for spin_code in spins_to_test:
        try:
            pkt = build_user_option_command(HIL_OPTION_SPIN, spin_code)
            await client._send_raw_command(pkt)
            await asyncio.sleep(delay_between_cmds)
            st = await client.get_state()
            raw = bytes.fromhex(st.raw_hex) if st.raw_hex else b""
            reported_spin_code = raw[8] if len(raw) > 8 else st.spin_speed_code
            rinse_hold_active = st.rinse_hold or (bool(raw[11] & 0x04) if len(raw) > 11 else False)

            # If sending a spin code triggered Rinse Hold or reverted, it is not a pure spin speed
            if reported_spin_code == spin_code and not rinse_hold_active:
                name = SPIN_SPEED_OPTIONS.get(spin_code)
                if name and name not in allowed_spins:
                    allowed_spins.append(name)
            elif rinse_hold_active:
                # Reset Rinse Hold modifier so state does not taint subsequent candidate probes
                try:
                    await client.set_rinse_hold(False)
                    await asyncio.sleep(delay_between_cmds)
                except Exception:
                    pass
        except Exception as exc:
            _LOGGER.debug("Spin probe error for code %d: %s", spin_code, exc)

    if not allowed_spins:
        allowed_spins = list(base_caps.allowed_spins)

    # 2. Probe Temperatures
    allowed_temps: list[str] = []
    temps_to_test = candidate_temps if candidate_temps is not None else CANDIDATE_TEMP_CODES
    for temp_code in temps_to_test:
        try:
            pkt = build_user_option_command(HIL_OPTION_TEMP, temp_code)
            await client._send_raw_command(pkt)
            await asyncio.sleep(delay_between_cmds)
            st = await client.get_state()
            raw = bytes.fromhex(st.raw_hex) if st.raw_hex else b""
            reported_temp_code = raw[10] if len(raw) > 10 else st.temperature_code

            if reported_temp_code == temp_code:
                name = TEMPERATURE_OPTIONS.get(temp_code)
                if name and name not in allowed_temps:
                    allowed_temps.append(name)
        except Exception as exc:
            _LOGGER.debug("Temp probe error for code %d: %s", temp_code, exc)

    if not allowed_temps:
        allowed_temps = list(base_caps.allowed_temps)

    # 3. Probe Extra Rinse max count
    max_extra_rinse = 0
    supports_extra_rinse = base_caps.supports_extra_rinse
    if supports_extra_rinse:
        for r_count in [1, 2, 3]:
            try:
                pkt = build_user_option_command(HIL_OPTION_EXTRA_RINSE, r_count)
                await client._send_raw_command(pkt)
                await asyncio.sleep(delay_between_cmds)
                st = await client.get_state()
                raw = bytes.fromhex(st.raw_hex) if st.raw_hex else b""
                reported_rinse = raw[9] if len(raw) > 9 else st.extra_rinse
                if reported_rinse == r_count:
                    max_extra_rinse = r_count
            except Exception:
                pass
        # Reset extra rinse back to 0
        try:
            await client._send_raw_command(build_user_option_command(HIL_OPTION_EXTRA_RINSE, 0))
            await asyncio.sleep(delay_between_cmds)
        except Exception:
            pass

    # 4. Probe Dry Modes (if Washer Dryer)
    allowed_dry: list[str] = ["No Dry"]
    supports_dry = base_caps.supports_dry
    if is_washer_dryer and supports_dry:
        for d_code in [1, 2, 7, 8]:
            try:
                pkt = build_user_option_command(HIL_OPTION_DRY, d_code)
                await client._send_raw_command(pkt)
                await asyncio.sleep(delay_between_cmds)
                st = await client.get_state()
                raw = bytes.fromhex(st.raw_hex) if st.raw_hex else b""
                reported_dry = raw[28] if len(raw) > 28 else st.dry_mode_code
                if reported_dry == d_code:
                    d_name = DRY_OPTIONS.get(d_code)
                    if d_name and d_name not in allowed_dry:
                        allowed_dry.append(d_name)
            except Exception:
                pass
        # Reset dry mode back to 0
        try:
            await client._send_raw_command(build_user_option_command(HIL_OPTION_DRY, 0))
            await asyncio.sleep(delay_between_cmds)
        except Exception:
            pass

    return ProgramCapabilities(
        allowed_temps=tuple(allowed_temps),
        allowed_spins=tuple(allowed_spins),
        supports_dry=len(allowed_dry) > 1 or supports_dry,
        allowed_dry_modes=tuple(allowed_dry) if len(allowed_dry) > 1 else base_caps.allowed_dry_modes,
        supports_steam=base_caps.supports_steam,
        supports_prewash=base_caps.supports_prewash,
        supports_soak=base_caps.supports_soak,
        supports_time_saver=base_caps.supports_time_saver,
        supports_extra_rinse=supports_extra_rinse and (max_extra_rinse > 0 or base_caps.supports_extra_rinse),
        supports_hot_rinse=base_caps.supports_hot_rinse,
        supports_rinse_hold=base_caps.supports_rinse_hold,
        supports_eco=base_caps.supports_eco,
        supports_aroma=base_caps.supports_aroma,
        supports_anti_crease=base_caps.supports_anti_crease,
    )


async def calibrate_appliance_quick(
    client: IFBWasherClient,
    program_map: dict[int, str],
    base_caps_map: dict[int, ProgramCapabilities],
    is_washer_dryer: bool = True,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    delay_between_cmds: float = 0.35,
) -> dict[int, ProgramCapabilities]:
    """Run a fast ~2m calibration on key daily programs (Mix/Daily, Cotton, Wash+Dry)."""
    # Ensure machine display and MCU are powered ON
    try:
        await client.turn_on()
        await asyncio.sleep(delay_between_cmds * 2)
    except Exception as exc:
        _LOGGER.debug("Could not send power on before quick calibration: %s", exc)

    calibrated_map: dict[int, ProgramCapabilities] = dict(base_caps_map)

    # Priority programs to calibrate quickly
    priority_codes: list[int] = []
    for code, name in program_map.items():
        clean = name.lower()
        if any(k in clean for k in ("mix", "daily", "cotton", "wash + dry", "wash+dry")):
            priority_codes.append(code)

    if not priority_codes:
        priority_codes = list(program_map.keys())[:3]

    total = len(priority_codes)
    for idx, code in enumerate(priority_codes):
        prog_name = program_map.get(code, f"Program {code}")
        if progress_callback:
            progress_callback(idx + 1, total, prog_name)
        base = base_caps_map.get(code, get_program_capabilities(code))
        calibrated_caps = await probe_single_program(
            client,
            program_code=code,
            base_caps=base,
            is_washer_dryer=is_washer_dryer,
            delay_between_cmds=delay_between_cmds,
        )
        calibrated_map[code] = calibrated_caps

    # Return machine to clean standby state
    try:
        first_code = list(program_map.keys())[0] if program_map else 1
        await client.select_program(first_code)
    except Exception:
        pass

    return calibrated_map


async def calibrate_appliance_simple(
    client: IFBWasherClient,
    program_map: dict[int, str],
    base_caps_map: dict[int, ProgramCapabilities],
    is_washer_dryer: bool = True,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    delay_between_cmds: float = 0.3,
) -> dict[int, ProgramCapabilities]:
    """Run a ~4-5 min model-constrained calibration across all dial programs."""
    # Ensure machine display and MCU are powered ON
    try:
        await client.turn_on()
        await asyncio.sleep(delay_between_cmds * 2)
    except Exception as exc:
        _LOGGER.debug("Could not send power on before simple calibration: %s", exc)

    calibrated_map: dict[int, ProgramCapabilities] = dict(base_caps_map)
    codes = list(program_map.keys())
    total = len(codes)

    for idx, code in enumerate(codes):
        prog_name = program_map.get(code, f"Program {code}")
        if progress_callback:
            progress_callback(idx + 1, total, prog_name)
        base = base_caps_map.get(code, get_program_capabilities(code))

        # Constrain candidate spins to expected model spins
        cand_spins: list[int] = []
        for s_name in base.allowed_spins:
            c = SPIN_NAME_TO_CODE.get(s_name)
            if c is not None and c not in cand_spins:
                cand_spins.append(c)

        # Constrain candidate temps to expected model temps
        cand_temps: list[int] = []
        for t_name in base.allowed_temps:
            c = TEMP_NAME_TO_CODE.get(t_name)
            if c is not None and c not in cand_temps:
                cand_temps.append(c)

        calibrated_caps = await probe_single_program(
            client,
            program_code=code,
            base_caps=base,
            is_washer_dryer=is_washer_dryer,
            delay_between_cmds=delay_between_cmds,
            candidate_spins=cand_spins if cand_spins else None,
            candidate_temps=cand_temps if cand_temps else None,
        )
        calibrated_map[code] = calibrated_caps

    # Return machine to clean standby state
    try:
        first_code = codes[0] if codes else 1
        await client.select_program(first_code)
    except Exception:
        pass

    return calibrated_map


async def calibrate_appliance_detailed(
    client: IFBWasherClient,
    program_map: dict[int, str],
    base_caps_map: dict[int, ProgramCapabilities],
    is_washer_dryer: bool = True,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    delay_between_cmds: float = 0.35,
) -> dict[int, ProgramCapabilities]:
    """Run an exhaustive ~15 min brute-force calibration across all dial positions."""
    # Ensure machine display and MCU are powered ON
    try:
        await client.turn_on()
        await asyncio.sleep(delay_between_cmds * 2)
    except Exception as exc:
        _LOGGER.debug("Could not send power on before detailed calibration: %s", exc)

    calibrated_map: dict[int, ProgramCapabilities] = dict(base_caps_map)
    codes = list(program_map.keys())
    total = len(codes)

    for idx, code in enumerate(codes):
        prog_name = program_map.get(code, f"Program {code}")
        if progress_callback:
            progress_callback(idx + 1, total, prog_name)
        base = base_caps_map.get(code, get_program_capabilities(code))
        calibrated_caps = await probe_single_program(
            client,
            program_code=code,
            base_caps=base,
            is_washer_dryer=is_washer_dryer,
            delay_between_cmds=delay_between_cmds,
        )
        calibrated_map[code] = calibrated_caps

    # Return machine to clean standby state
    try:
        first_code = codes[0] if codes else 1
        await client.select_program(first_code)
    except Exception:
        pass

    return calibrated_map


from datetime import datetime, timezone
import json
import os


def serialize_capabilities_map(
    caps_map: dict[int, ProgramCapabilities],
    mode: str = "simple",
    model: Optional[str] = None,
    family: Optional[str] = None,
) -> dict[str, Any]:
    """Serialize program capabilities map to a structured JSON envelope with metadata (host redacted)."""
    raw_caps = {str(code): caps.to_dict() for code, caps in caps_map.items()}
    return {
        "schema_version": 1,
        "calibration_mode": mode,
        "calibrated_at": datetime.now(timezone.utc).isoformat(),
        "appliance_family": family or "washer_dryer",
        "model": model or "IFB Washing Machine",
        "programs_count": len(caps_map),
        "capabilities": raw_caps,
    }


def extract_profile_metadata(data: dict[str, Any]) -> dict[str, Any]:
    """Extract profile metadata from either an envelope or a legacy dictionary."""
    if isinstance(data, dict) and "capabilities" in data and isinstance(data["capabilities"], dict):
        return {
            "schema_version": data.get("schema_version", 1),
            "calibration_mode": data.get("calibration_mode", "simple"),
            "calibrated_at": data.get("calibrated_at"),
            "appliance_family": data.get("appliance_family", "washer_dryer"),
            "model": data.get("model", "IFB Washing Machine"),
            "programs_count": data.get("programs_count", len(data["capabilities"])),
        }
    # Legacy raw dictionary fallback
    return {
        "schema_version": 1,
        "calibration_mode": "legacy",
        "calibrated_at": None,
        "appliance_family": "washer_dryer",
        "model": "IFB Washing Machine",
        "programs_count": len(data) if isinstance(data, dict) else 0,
    }


def deserialize_capabilities_map(data: dict[str, Any]) -> dict[int, ProgramCapabilities]:
    """Deserialize program capabilities map from either an envelope or legacy dict."""
    result: dict[int, ProgramCapabilities] = {}
    if not isinstance(data, dict):
        return result

    # Check for envelope format
    target_caps = data.get("capabilities", data)
    if not isinstance(target_caps, dict):
        return result

    for code_str, caps_dict in target_caps.items():
        try:
            code = int(code_str)
            if isinstance(caps_dict, dict):
                result[code] = ProgramCapabilities.from_dict(caps_dict)
        except (ValueError, TypeError):
            continue
    return result


def save_profile_backup(
    config_dir: str,
    caps_map: dict[int, ProgramCapabilities],
    mode: str = "simple",
    model: Optional[str] = None,
    family: Optional[str] = None,
) -> str:
    """Save calibrated profile to a standalone JSON file in config_dir/ifb_washer_profiles/."""
    profiles_dir = os.path.join(config_dir, "ifb_washer_profiles")
    os.makedirs(profiles_dir, exist_ok=True)

    clean_model = (model or "ifb_washer").lower().replace(" ", "_").replace("/", "_").replace(".", "_")
    filename = f"{clean_model}_profile.json"
    filepath = os.path.join(profiles_dir, filename)

    payload = serialize_capabilities_map(caps_map, mode=mode, model=model, family=family)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return filepath
