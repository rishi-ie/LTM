from pathlib import Path

import pytest

from ltm_r2.codec import pack_program, unpack_program
from ltm_r2.engine import equivalent, execute_oracle, execute_program, migrate, structural_variant
from ltm_r2.generator import compile_body, make_body
from ltm_r2.profiles import PROFILES, compile_profile, dynamics_variant


def test_all_profiles_match_independent_semantic_oracle() -> None:
    body = make_body(36, seed=1811)
    program = compile_body(body)
    for profile in PROFILES.values():
        compiled = compile_profile(profile)
        assert equivalent(execute_program(program, compiled), execute_oracle(body, compiled))


def test_packed_round_trip_keeps_semantic_and_artifact_hashes(tmp_path: Path) -> None:
    program = compile_body(make_body(7, seed=1811))
    pack_program(tmp_path, program)
    restored = unpack_program(tmp_path)
    assert restored.substrate_sha256 == program.substrate_sha256
    assert restored.artifact_sha256 == program.artifact_sha256
    assert restored.archive_sha256 == program.archive_sha256


def test_tiered_profile_switches_have_distinct_safe_behavior() -> None:
    program = compile_body(make_body(9, seed=1811))
    reasoning = compile_profile(PROFILES["reasoning"])
    dynamics = compile_profile(dynamics_variant(PROFILES["reasoning"], 1.5))
    structural = compile_profile(structural_variant(PROFILES["reasoning"]))
    first = migrate(program, reasoning, dynamics, 1)
    second = migrate(program, reasoning, structural, 2)
    third = migrate(program, reasoning, dynamics, 3)
    assert first.disposition == "switched" and not first.affected_unit_ids
    assert set(second.affected_unit_ids).isdisjoint(second.unchanged_unit_ids)
    assert third.disposition == "SOURCE_RECOMPILATION_REQUIRED"


def test_invalid_profile_opcode_fails_closed() -> None:
    profile = PROFILES["reasoning"]
    broken = profile.__class__(
        profile.profile_id, profile.revision, profile.mumbrane_schema_revision,
        profile.operator_bank_revision, profile.active_operator_ids,
        (("implies", "not-an-opcode"),), profile.soft_opcodes,
        profile.required_feature_mask, profile.dynamics_weight, profile.profile_sha256,
    )
    with pytest.raises(ValueError, match="UNKNOWN_PROFILE_OPCODE"):
        compile_profile(broken)
