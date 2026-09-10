"""Model lookup engine and capability resolver for IFB Washing Machines."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .const import ApplianceArchetype, ManualInfo, ModelInfo, ProgramCapabilities

DATA_DIR = Path(__file__).parent / "data"


def _normalize_name(name: str) -> str:
    """Normalize a model name or string for fuzzy comparison."""
    name = name.strip().upper()
    # Strip common vendor prefixes/suffixes
    name = re.sub(r"^IFB\s+", "", name)
    name = re.sub(r"[\s\-_/]+", " ", name)
    return name


_GLOBAL_LOOKUP: WasherModelLookup | None = None


def get_lookup() -> WasherModelLookup:
    """Get or create singleton WasherModelLookup instance."""
    global _GLOBAL_LOOKUP
    if _GLOBAL_LOOKUP is None:
        _GLOBAL_LOOKUP = WasherModelLookup()
    return _GLOBAL_LOOKUP


class WasherModelLookup:
    """Lookup engine for IFB smart washing machines and washer-dryers."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self._data_dir = data_dir or DATA_DIR
        self._models: list[ModelInfo] = []
        self._models_by_name: dict[str, ModelInfo] = {}
        self._models_by_normalized: dict[str, ModelInfo] = {}
        self._manuals: dict[str, ManualInfo] = {}
        self._programs: list[dict[str, Any]] = []
        self._gating: dict[tuple[str, str], ProgramCapabilities] = {}
        self._special_features: list[dict[str, Any]] = []
        self._archetypes: dict[str, Any] = []
        self._aliases_by_normalized: dict[str, str] = {}
        self._load_data()


    def _load_data(self) -> None:
        """Load JSON datasets into indexed memory."""
        # 1. Manuals
        manuals_file = self._data_dir / "manuals.json"
        if manuals_file.exists():
            with open(manuals_file, "r", encoding="utf-8") as f:
                for item in json.load(f):
                    m = ManualInfo(
                        id=item["id"],
                        manual_code=item["manual_code"],
                        file_name=item["file_name"],
                        archetype=item["archetype"],
                        model_series=item["model_series"],
                        page_count=item["page_count"],
                        panel_page=item["panel_page"],
                        prog_table_page=item["prog_table_page"],
                        panel_image_path=item["panel_image_path"],
                    )
                    self._manuals[m.manual_code] = m

        # 2. Models
        models_file = self._data_dir / "models.json"
        if models_file.exists():
            with open(models_file, "r", encoding="utf-8") as f:
                for item in json.load(f):
                    m = ModelInfo(
                        id=item["id"],
                        manual_code=item["manual_code"],
                        model_name=item["model_name"],
                        series=item["series"],
                        finish_code=item["finish_code"],
                        capacity_kg=float(item["capacity_kg"]),
                        spin_max_rpm=int(item["spin_max_rpm"]),
                        archetype=item["archetype"],
                    )
                    self._models.append(m)
                    self._models_by_name[m.model_name.lower()] = m
                    self._models_by_normalized[_normalize_name(m.model_name)] = m

        # 3. Programs
        programs_file = self._data_dir / "programs.json"
        if programs_file.exists():
            with open(programs_file, "r", encoding="utf-8") as f:
                self._programs = json.load(f)

        # 4. Program Gating
        gating_file = self._data_dir / "program_gating.json"
        if gating_file.exists():
            with open(gating_file, "r", encoding="utf-8") as f:
                for item in json.load(f):
                    caps = ProgramCapabilities(
                        program_name=item["program_name"],
                        allowed_temps=tuple(item.get("allowed_temps") or ()),
                        allowed_spins=tuple(item.get("allowed_spins") or ()),
                        supports_dry=bool(item.get("supports_dry")),
                        allowed_dry_modes=tuple(item.get("allowed_dry_modes") or ("No Dry",)),
                        max_dry_time_min=int(item.get("max_dry_time_min") or 0),
                        supports_steam=bool(item.get("supports_steam")),
                        steam_behavior=str(item.get("steam_behavior") or "none"),
                        supports_prewash=bool(item.get("supports_prewash")),
                        supports_soak=bool(item.get("supports_soak")),
                        supports_time_saver=bool(item.get("supports_time_saver")),
                        supports_extra_rinse=bool(item.get("supports_extra_rinse", True)),
                        max_extra_rinses=int(item.get("max_extra_rinses") or 3),
                        supports_hot_rinse=bool(item.get("supports_hot_rinse")),
                        requires_extra_rinse_for_hot_rinse=bool(item.get("requires_extra_rinse_for_hot_rinse", True)),
                        supports_rinse_hold=bool(item.get("supports_rinse_hold", True)),
                        supports_eco=bool(item.get("supports_eco")),
                        supports_aroma=bool(item.get("supports_aroma")),
                        supports_anti_crease=bool(item.get("supports_anti_crease")),
                        supports_delay_start=bool(item.get("supports_delay_start", True)),
                    )
                    # Index by (manual_code, program_name.lower())
                    key = (item["manual_code"], item["program_name"].lower())
                    self._gating[key] = caps

        # 5. Special features
        special_file = self._data_dir / "special_features.json"
        if special_file.exists():
            with open(special_file, "r", encoding="utf-8") as f:
                self._special_features = json.load(f)

        # 6. Archetypes
        archetypes_file = self._data_dir / "archetypes.json"
        if archetypes_file.exists():
            with open(archetypes_file, "r", encoding="utf-8") as f:
                self._archetypes = json.load(f)

        # 7. Aliases
        aliases_file = self._data_dir / "aliases.json"
        if aliases_file.exists():
            with open(aliases_file, "r", encoding="utf-8") as f:
                for item in json.load(f):
                    alias = item.get("alias_name")
                    canonical = item.get("canonical_name")
                    if alias and canonical:
                        self._aliases_by_normalized[_normalize_name(alias)] = canonical

    def get_model_info(self, model_name: str) -> ModelInfo | None:
        """Find model information by exact or normalized commercial model name."""
        if not model_name:
            return None
        # 1. Exact match (case-insensitive)
        if model_name.lower() in self._models_by_name:
            return self._models_by_name[model_name.lower()]

        # 2. Normalized match
        norm = _normalize_name(model_name)
        if norm in self._models_by_normalized:
            return self._models_by_normalized[norm]

        # 3. Alias match
        if norm in self._aliases_by_normalized:
            target = self._aliases_by_normalized[norm]
            target_norm = _normalize_name(target)
            if target_norm in self._models_by_normalized:
                return self._models_by_normalized[target_norm]

        # 4. Substring / Token matching
        for model in self._models:
            m_norm = _normalize_name(model.model_name)
            if norm in m_norm or m_norm in norm:
                return model

        return None

    def get_manual_info(self, manual_code: str) -> ManualInfo | None:
        """Find manual information by manual code (e.g. 'MAN_742_E')."""
        return self._manuals.get(manual_code)

    def get_program_capabilities(
        self, manual_code: str, program_name: str
    ) -> ProgramCapabilities | None:
        """Look up capability gating for a program under a specific manual."""
        key = (manual_code, program_name.lower())
        if key in self._gating:
            return self._gating[key]

        # Fuzzy match program name under same manual
        prog_norm = _normalize_name(program_name)
        for (m_code, p_name), caps in self._gating.items():
            if m_code == manual_code and _normalize_name(p_name) == prog_norm:
                return caps

        # Fallback to default Washer-Dryer manual MAN_742_E if manual is unknown
        fallback_key = ("MAN_742_E", program_name.lower())
        if fallback_key in self._gating:
            return self._gating[fallback_key]

        return None

    def get_programs_for_manual(self, manual_code: str) -> list[dict[str, Any]]:
        """Get all wash programs defined for a manual."""
        return [p for p in self._programs if p.get("manual_code") == manual_code]

    def get_dial_programs(self, manual_code: str) -> dict[int, str]:
        """Return physical rotary switch detent-to-program mapping (1..15)."""
        dial: dict[int, str] = {}
        for p in self._programs:
            if p.get("manual_code") == manual_code:
                pos = p.get("physical_position")
                if pos is not None:
                    dial[int(pos)] = p["program_name"]
        return dial

    def get_special_features_for_manual(self, manual_code: str) -> list[dict[str, Any]]:
        """Return special button combo features (Tub Clean, AP Mode) for a manual."""
        return [sf for sf in self._special_features if sf.get("manual_code") == manual_code]

    def get_archetype_info(self, archetype_name: str) -> dict[str, Any] | None:
        """Return archetype technical specifications."""
        return self._archetypes.get(archetype_name)

    @property
    def all_models(self) -> list[ModelInfo]:
        """Return all tracked commercial models."""
        return list(self._models)

    @property
    def all_manuals(self) -> list[ManualInfo]:
        """Return all audited manuals."""
        return list(self._manuals.values())
