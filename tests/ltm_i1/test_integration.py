from __future__ import annotations

from pathlib import Path

from ltm.adapters import from_g1
from ltm.codec import artifact_hash, pack_program, semantic_hash, unpack_program
from ltm_i1.generator import cases
from ltm_i1.runner import run_case
from topology_g1.fixtures import fixtures


def test_packed_reload_preserves_semantics_and_artifact(tmp_path: Path):
    fixture = fixtures("development")[0]
    program, archive = from_g1(fixture.nodes, (fixture.relation,))
    manifest = pack_program(tmp_path, program, archive)
    loaded = unpack_program(tmp_path, program.config, archive)
    assert manifest.semantic_sha256 == semantic_hash(loaded)
    assert manifest.artifact_sha256 == artifact_hash(loaded)


def test_canonical_case_roundtrip(tmp_path: Path):
    result = run_case(cases("development", 1, 1801)[0], tmp_path)
    assert result.failure_codes == ()
    assert result.semantic_equal and result.artifact_equal and result.projection_equal
    assert result.hard_equal and result.soft_equal and result.g9_equal


def test_all_registered_fixture_families_are_represented():
    names = {item.family for item in cases("development", 128, 1801)}
    assert names == {item.family for item in fixtures("development")}

