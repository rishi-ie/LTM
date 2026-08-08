"""Canonical FieldIR hashing and immutable vector sidecars."""

from __future__ import annotations

import hashlib
import json
import math
import struct
from collections.abc import Iterable, Mapping
from dataclasses import asdict, is_dataclass
from pathlib import Path

from .schemas import FieldProgram

_MAGIC = b"LTMFV1\0"


def _plain(value: object) -> object:
    if is_dataclass(value):
        return _plain(asdict(value))
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in sorted(value.items())}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def canonical_json(value: object) -> str:
    return json.dumps(_plain(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def semantic_digest(program: FieldProgram) -> str:
    """Hash executable meaning, intentionally excluding all vector artifacts."""
    return _hash(
        {
            "schema_version": program.schema_version,
            "program_id": program.program_id,
            "registry_sha256": program.registry_sha256,
            "atoms": [
                {
                    "atom_id": atom.atom_id,
                    "kind": atom.kind,
                    "canonical_text": atom.canonical_text,
                    "occurrence_text": atom.occurrence_text,
                    "source_id": atom.source_id,
                    "source_start": atom.source_start,
                    "source_end": atom.source_end,
                    "context": atom.context,
                    "provenance_sha256": atom.provenance_sha256,
                }
                for atom in program.atoms
            ],
            "factors": [
                {
                    "factor_id": factor.factor_id,
                    "relation_type": factor.relation_type,
                    "role_bindings": factor.role_bindings,
                    "context": factor.context,
                    "provenance_sha256": factor.provenance_sha256,
                    "base_weight": factor.base_weight,
                }
                for factor in program.factors
            ],
        }
    )


def artifact_digest(program: FieldProgram) -> str:
    return _hash({"semantic_digest": semantic_digest(program), "artifacts": program.vector_spaces, "program": program})


def _row_bytes(values: Iterable[float]) -> bytes:
    return b"".join(struct.pack("<f", value) for value in values)


def write_vector_sidecar(path: Path, rows: Iterable[Iterable[float]], dimension: int) -> tuple[str, tuple[str, ...]]:
    materialized = [tuple(float(value) for value in row) for row in rows]
    if dimension <= 0 or any(len(row) != dimension for row in materialized):
        raise ValueError("sidecar row dimension mismatch")
    payload = b"".join(_row_bytes(row) for row in materialized)
    header = _MAGIC + struct.pack("<II", dimension, len(materialized))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + payload)
    return hashlib.sha256(header + payload).hexdigest(), tuple(
        hashlib.sha256(_row_bytes(row)).hexdigest() for row in materialized
    )


def read_vector_sidecar(path: Path, expected_sha256: str, row_index: int, expected_row_sha256: str) -> tuple[float, ...]:
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != expected_sha256:
        raise ValueError("sidecar hash mismatch")
    if len(content) < len(_MAGIC) + 8 or content[: len(_MAGIC)] != _MAGIC:
        raise ValueError("sidecar header mismatch")
    dimension, count = struct.unpack("<II", content[len(_MAGIC) : len(_MAGIC) + 8])
    if row_index >= count:
        raise ValueError("sidecar row is absent")
    offset = len(_MAGIC) + 8 + row_index * dimension * 4
    row = content[offset : offset + dimension * 4]
    if len(row) != dimension * 4 or hashlib.sha256(row).hexdigest() != expected_row_sha256:
        raise ValueError("sidecar row hash mismatch")
    return struct.unpack(f"<{dimension}f", row)


def verify_vector_artifacts(program: FieldProgram, sidecars: Mapping[str, Path]) -> None:
    """Verify every referenced vector row against its declared space contract."""
    spaces = {space.space_id: space for space in program.vector_spaces}
    references = []
    for atom in program.atoms:
        references.extend(ref for ref in (atom.canonical_vector, atom.occurrence_vector) if ref)
    for factor in program.factors:
        references.extend(ref for ref in (factor.operator_vector, *factor.role_vectors, *factor.binding_vectors) if ref)
    for ref in references:
        if ref.sidecar_sha256 not in sidecars or ref.space_id not in spaces:
            raise ValueError("vector artifact is absent")
        vector = read_vector_sidecar(sidecars[ref.sidecar_sha256], ref.sidecar_sha256, ref.row_index, ref.row_sha256)
        space = spaces[ref.space_id]
        if len(vector) != space.dimension or not all(math.isfinite(value) for value in vector):
            raise ValueError("vector artifact violates its space")
        if space.normalized:
            norm = math.sqrt(sum(value * value for value in vector))
            if not math.isclose(norm, 1.0, rel_tol=1e-5, abs_tol=1e-5):
                raise ValueError("normalized vector artifact has invalid norm")
