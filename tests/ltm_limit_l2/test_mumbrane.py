from __future__ import annotations

from ltm_limit_l2.compiler import compile_statement, source
from ltm_r2.codec import pack_program, semantic_hash, unpack_program


def test_formal_body_mumbrane_round_trip_and_packed_reload(tmp_path):
    result = compile_statement(source("x + 0 = x"))
    assert result.body is not None and result.mumbrane_program is not None
    program = result.mumbrane_program
    original = semantic_hash(program)
    pack_program(tmp_path, program)
    loaded = unpack_program(tmp_path)
    assert semantic_hash(loaded) == original
    assert any("x + 0" in row[1] for row in loaded.source_archive)
    assert all(b"x + 0" not in (tmp_path / name).read_bytes() for name in ("units.bin", "ports.bin", "coordinates.bin", "vectors.bin"))
