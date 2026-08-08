"""Deterministic packing and hash boundaries for Mumbrane IR v1."""

from __future__ import annotations

import hashlib
import json
import os
import struct
from dataclasses import asdict, replace
from pathlib import Path

from .schemas import (
    MUMBRANE_SCHEMA,
    MumbraneCoordinate,
    MumbranePort,
    MumbraneProgram,
    MumbraneUnit,
    MumbraneVectorBundle,
)

_NONE = 0xFFFFFFFF
_UNIT = struct.Struct("<QHHIIIIII f I 20s".replace(" ", ""))
_PORT = struct.Struct("<IHHIIII")
_COORDINATE = struct.Struct("<IHHfffI")
_BUNDLE = struct.Struct("<IIIII")


def canonical_json(value: object) -> str:
    if hasattr(value, "__dataclass_fields__"):
        value = asdict(value)
    if isinstance(value, dict):
        value = {key: json.loads(canonical_json(item)) for key, item in sorted(value.items())}
    elif isinstance(value, (tuple, list)):
        value = [json.loads(canonical_json(item)) for item in value]
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def _substrate_payload(
    units: tuple[MumbraneUnit, ...], ports: tuple[MumbranePort, ...], coordinates: tuple[MumbraneCoordinate, ...], symbols: tuple[str, ...]
) -> dict[str, object]:
    return {
        "schema": MUMBRANE_SCHEMA,
        "units": [asdict(item) for item in sorted(units, key=lambda item: item.unit_id)],
        "ports": [asdict(item) for item in sorted(ports, key=lambda item: (item.source_unit_index, item.role_code, item.ordinal, item.target_unit_index))],
        "coordinates": [asdict(item) for item in sorted(coordinates, key=lambda item: (item.unit_index, item.axis_code, item.value_code))],
        "symbols": list(symbols),
    }


def make_program(
    units: tuple[MumbraneUnit, ...],
    ports: tuple[MumbranePort, ...],
    coordinates: tuple[MumbraneCoordinate, ...],
    vector_bundles: tuple[MumbraneVectorBundle, ...],
    vectors: tuple[tuple[float, ...], ...],
    symbols: tuple[str, ...],
    source_archive: tuple[tuple[str, str], ...],
) -> MumbraneProgram:
    def f32(value: float | None) -> float | None:
        return None if value is None else struct.unpack("<f", struct.pack("<f", value))[0]
    units = tuple(replace(item, base_weight=f32(item.base_weight)) for item in units)
    coordinates = tuple(replace(
        item, scalar_value=f32(item.scalar_value), lower_bound=f32(item.lower_bound), upper_bound=f32(item.upper_bound)
    ) for item in coordinates)
    vectors = tuple(
        tuple(struct.unpack("<f", struct.pack("<f", value))[0] for value in row)
        for row in vectors
    )
    substrate = digest(_substrate_payload(units, ports, coordinates, symbols))
    artifact = digest({"substrate": substrate, "bundles": vector_bundles, "vectors": vectors})
    archive = digest({"archive": source_archive})
    return MumbraneProgram(MUMBRANE_SCHEMA, units, ports, coordinates, vector_bundles, vectors, symbols, source_archive, substrate, artifact, archive)


def semantic_hash(program: MumbraneProgram) -> str:
    return digest(_substrate_payload(program.units, program.ports, program.coordinates, program.symbols))


def artifact_hash(program: MumbraneProgram) -> str:
    return digest({"substrate": semantic_hash(program), "bundles": program.vector_bundles, "vectors": program.vectors})


def archive_hash(program: MumbraneProgram) -> str:
    return digest({"archive": program.source_archive})


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def pack_program(root: Path, program: MumbraneProgram) -> dict[str, object]:
    """Pack active numeric rows separately from the source archive."""
    symbol_index = {value: index for index, value in enumerate(program.symbols)}
    vector_dim = len(program.vectors[0]) if program.vectors else 0
    if any(len(row) != vector_dim for row in program.vectors):
        raise ValueError("VECTOR_ARTIFACT_MISMATCH")
    def optional(value: int | None) -> int:
        return _NONE if value is None else value
    units = b"".join(_UNIT.pack(
        symbol_index[item.unit_id], item.unit_class_code, item.semantic_code,
        item.feature_mask, item.port_start, item.port_count, item.coordinate_start,
        item.coordinate_count, optional(item.vector_bundle_index), item.base_weight,
        item.flags, bytes.fromhex(item.semantic_sha256)[:20],
    ) for item in program.units)
    ports = b"".join(_PORT.pack(
        item.source_unit_index, item.role_code, item.ordinal, item.target_unit_index,
        optional(item.role_vector_index), optional(item.binding_vector_index), item.flags,
    ) for item in program.ports)
    coordinates = b"".join(_COORDINATE.pack(
        item.unit_index, item.axis_code, item.value_code,
        float("nan") if item.scalar_value is None else item.scalar_value,
        float("nan") if item.lower_bound is None else item.lower_bound,
        float("nan") if item.upper_bound is None else item.upper_bound,
        0,
    ) for item in program.coordinates)
    bundles = b"".join(_BUNDLE.pack(*[optional(value) for value in (
        item.content_vector, item.operator_vector, item.role_vector, item.context_vector, item.binding_vector,
    )]) for item in program.vector_bundles)
    vectors = b"".join(struct.pack(f"<{vector_dim}f", *row) for row in program.vectors)
    tables = {
        "units": units,
        "unit_hashes": b"".join(bytes.fromhex(item.semantic_sha256) for item in program.units),
        "ports": ports,
        "coordinates": coordinates,
        "bundles": bundles,
        "vectors": vectors,
        "symbols": canonical_json(program.symbols).encode(),
    }
    table_hashes = {name: hashlib.sha256(value).hexdigest() for name, value in tables.items()}
    manifest = {
        "schema_revision": MUMBRANE_SCHEMA,
        "substrate_sha256": program.substrate_sha256,
        "artifact_sha256": program.artifact_sha256,
        "archive_sha256": program.archive_sha256,
        "table_hashes": table_hashes,
        "byte_lengths": {name: len(value) for name, value in tables.items()},
        "row_counts": {
            "units": len(program.units), "ports": len(program.ports), "coordinates": len(program.coordinates),
            "bundles": len(program.vector_bundles), "vectors": len(program.vectors), "symbols": len(program.symbols), "unit_hashes": len(program.units),
        },
        "vector_dimension": vector_dim,
    }
    for name, payload in tables.items():
        _write_atomic(root / f"{name}.bin", payload)
    _write_atomic(root / "archive.json", canonical_json(program.source_archive).encode())
    _write_atomic(root / "manifest.json", canonical_json(manifest).encode())
    return manifest


def _read_json(root: Path, name: str):
    return json.loads((root / name).read_text())


def unpack_program(root: Path) -> MumbraneProgram:
    manifest = _read_json(root, "manifest.json")
    if manifest["schema_revision"] != MUMBRANE_SCHEMA:
        raise ValueError("PROFILE_SCHEMA_MISMATCH")
    for name, expected in manifest["table_hashes"].items():
        payload = (root / f"{name}.bin").read_bytes()
        if hashlib.sha256(payload).hexdigest() != expected or len(payload) != manifest["byte_lengths"][name]:
            raise ValueError("UNIT_HASH_MISMATCH")
    symbols = tuple(_read_json(root, "symbols.bin"))
    def rows(name: str, structure: struct.Struct):
        payload = (root / f"{name}.bin").read_bytes()
        if len(payload) % structure.size:
            raise ValueError("UNIT_HASH_MISMATCH")
        return tuple(structure.unpack_from(payload, offset) for offset in range(0, len(payload), structure.size))
    raw_hashes = (root / "unit_hashes.bin").read_bytes()
    if len(raw_hashes) != manifest["row_counts"]["units"] * 32:
        raise ValueError("UNIT_HASH_MISMATCH")
    units = []
    for index, row in enumerate(rows("units", _UNIT)):
        identity, unit_class, semantic, mask, port_start, port_count, coordinate_start, coordinate_count, bundle, weight, flags, _prefix = row
        try:
            unit_id = symbols[identity]
        except IndexError as exc:
            raise ValueError("UNIT_HASH_MISMATCH") from exc
        units.append(MumbraneUnit(unit_id, MUMBRANE_SCHEMA, unit_class, semantic, mask, port_start, port_count, coordinate_start, coordinate_count, None if bundle == _NONE else bundle, weight, flags, raw_hashes[index * 32 : (index + 1) * 32].hex()))
    ports = tuple(MumbranePort(source, role, ordinal, target, None if role_vector == _NONE else role_vector, None if binding_vector == _NONE else binding_vector, flags) for source, role, ordinal, target, role_vector, binding_vector, flags in rows("ports", _PORT))
    def none_if_nan(value: float) -> float | None:
        return None if __import__("math").isnan(value) else value
    coordinates = tuple(MumbraneCoordinate(unit, axis, value_code, none_if_nan(scalar), none_if_nan(lower), none_if_nan(upper)) for unit, axis, value_code, scalar, lower, upper, _reserved in rows("coordinates", _COORDINATE))
    bundles = tuple(MumbraneVectorBundle(*[None if value == _NONE else value for value in row]) for row in rows("bundles", _BUNDLE))
    vector_dimension = int(manifest["vector_dimension"])
    vector_payload = (root / "vectors.bin").read_bytes()
    width = max(1, vector_dimension) * 4
    if vector_dimension == 0:
        vectors = ()
    elif len(vector_payload) % width:
        raise ValueError("VECTOR_ARTIFACT_MISMATCH")
    else:
        vectors = tuple(tuple(float(value) for value in struct.unpack_from(f"<{vector_dimension}f", vector_payload, offset)) for offset in range(0, len(vector_payload), width))
    archive = tuple(tuple(item) for item in _read_json(root, "archive.json"))
    program = MumbraneProgram(MUMBRANE_SCHEMA, tuple(units), ports, coordinates, bundles, vectors, symbols, archive, manifest["substrate_sha256"], manifest["artifact_sha256"], manifest["archive_sha256"])
    if semantic_hash(program) != program.substrate_sha256 or artifact_hash(program) != program.artifact_sha256 or archive_hash(program) != program.archive_sha256:
        raise ValueError("UNIT_HASH_MISMATCH")
    return program


def active_byte_count(root: Path) -> int:
    return sum((root / f"{name}.bin").stat().st_size for name in ("units", "ports", "coordinates", "bundles", "vectors", "symbols"))


def tamper_program(program: MumbraneProgram, *, swap_first_port: bool = False) -> MumbraneProgram:
    """Test-only corruption helper that preserves syntactic validity."""
    if not swap_first_port or len(program.ports) < 2:
        return program
    ports = list(program.ports)
    ports[0], ports[1] = ports[1], ports[0]
    return make_program(program.units, tuple(ports), program.coordinates, program.vector_bundles, program.vectors, program.symbols, program.source_archive)
