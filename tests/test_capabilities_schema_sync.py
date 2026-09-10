"""Test schema synchronization between ifb_washer_local and ifb_washer_models."""

import dataclasses
from ifb_washer_local.const import ProgramCapabilities as LocalProgramCapabilities
from custom_components.ifb_washer_local.ifb_washer_models.const import (
    ProgramCapabilities as ModelsProgramCapabilities,
)


def test_program_capabilities_fields_match():
    """Ensure both ProgramCapabilities dataclasses define identical field sets."""
    local_fields = {f.name: f.type for f in dataclasses.fields(LocalProgramCapabilities)}
    models_fields = {f.name: f.type for f in dataclasses.fields(ModelsProgramCapabilities)}

    assert local_fields.keys() == models_fields.keys(), (
        f"Field mismatch between Local ({set(local_fields.keys()) - set(models_fields.keys())}) "
        f"and Models ({set(models_fields.keys()) - set(local_fields.keys())})"
    )


def test_program_capabilities_to_dict_keys_match():
    """Ensure to_dict() returns identical key sets between both models."""
    local_dict = LocalProgramCapabilities(program_name="Cotton").to_dict()
    models_dict = ModelsProgramCapabilities(program_name="Cotton").to_dict()

    assert set(local_dict.keys()) == set(models_dict.keys()), (
        f"to_dict key mismatch: Local={set(local_dict.keys()) - set(models_dict.keys())}, "
        f"Models={set(models_dict.keys()) - set(local_dict.keys())}"
    )
