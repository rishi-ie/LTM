"""Deterministic numeric packing and hash boundaries for FieldIR v2."""

from __future__ import annotations

import hashlib
import json
import os
import struct
from dataclasses import asdict, is_dataclass
from pathlib import Path

from .schema import (
    SCHEMA_VERSION,
    AtomRecord,
    BindingRecord,
    ContextRecord,
    FactorRecord,
    FieldManifestV2,
    FieldProgramV2,
    ProvenanceRecord,
    SourceArchive,
    SourceArchiveRecord,
    SurfaceClaimRecord,
    VectorRef,
)

_NONE = 0xFFFFFFFF
_ATOM = struct.Struct("<QHHIIIIIII")
_FACTOR = struct.Struct("<QHHIIIHHIIffffQI")
_BINDING = struct.Struct("<IHHIIII")
_CONTEXT = struct.Struct("<IHHii3fIII")
_PROVENANCE = struct.Struct("<Qii32s")
_VECTOR = struct.Struct("<QII32s32s")
_MODALITIES = {"asserted": 1, "conditional": 2, "hypothetical": 3, "uncertain": 4, "observed": 5}


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


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: object) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def _config_semantics(program: FieldProgramV2) -> dict[str, object]:
    return {
        "revision": program.config.revision,
        "registry_sha256": program.config.registry_sha256,
        "relation_codes": program.config.relation_codes,
        "role_codes": program.config.role_codes,
        "node_kind_codes": program.config.node_kind_codes,
        "factor_record_bytes": program.config.factor_record_bytes,
        "binding_record_bytes": program.config.binding_record_bytes,
    }


def _context_semantics(context) -> dict[str, object]:
    """Return semantic context fields without vector-artifact references."""
    # Packed contexts use float32.  Hash the canonical packed value so an
    # in-memory Python float and its reloaded float32 representation compare
    # as the same semantic record.
    def f32(value: float) -> float:
        return struct.unpack("<f", struct.pack("<f", value))[0]

    return {
        "scope_key": context.scope_key,
        "polarity": context.polarity,
        "modality": context.modality,
        "valid_from": context.valid_from,
        "valid_to": context.valid_to,
        "confidence": f32(context.confidence),
        "authority": f32(context.authority),
        "priority": f32(context.priority),
    }


def _semantic_payload(program: FieldProgramV2) -> dict[str, object]:
    atom_rows = []
    for atom in sorted(program.atoms, key=lambda item: item.atom_id):
        context = _context_semantics(program.contexts[atom.context_index])
        provenance = asdict(program.provenances[atom.provenance_index])
        atom_rows.append({
            "atom_id": atom.atom_id,
            "kind_code": atom.kind_code,
            "source_key": atom.source_key,
            "source_start": atom.source_start,
            "source_end": atom.source_end,
            "context": context,
            "provenance": provenance,
        })
    atom_ids = {item.atom_id for item in program.atoms}
    factor_rows = []
    for factor in sorted(program.factors, key=lambda item: item.factor_id):
        original = next(item for item in program.factors if item.factor_id == factor.factor_id)
        bindings = program.bindings[original.binding_start : original.binding_start + original.binding_count]
        factor_rows.append({
            "factor_id": factor.factor_id,
            "operator_code": factor.operator_code,
            "region_index": factor.region_index,
            "base_weight": factor.base_weight,
            "context": _context_semantics(program.contexts[factor.context_index]),
            "provenance": asdict(program.provenances[factor.provenance_index]),
            "bindings": [
                {
                    "role_code": binding.role_code,
                    "ordinal": binding.ordinal,
                    "atom_id": program.atoms[binding.atom_index].atom_id,
                }
                for binding in sorted(bindings, key=lambda item: (item.role_code, item.ordinal, item.atom_index))
                if program.atoms[binding.atom_index].atom_id in atom_ids
            ],
        })
    return {
        "schema_version": program.schema_version,
        "config": _config_semantics(program),
        "atoms": atom_rows,
        "factors": factor_rows,
    }


def semantic_hash(program: FieldProgramV2) -> str:
    """Hash exact topology while intentionally excluding vector artifacts."""
    return sha256_json(_semantic_payload(program))


def artifact_hash(program: FieldProgramV2) -> str:
    return sha256_json({
        "semantic_hash": semantic_hash(program),
        "vector_spaces": program.config.vector_spaces,
        "vectors": program.vectors,
    })


def archive_hash(archive: SourceArchive | None) -> str | None:
    if archive is None:
        return None
    return sha256_json({
        "revision": archive.revision,
        "records": sorted(archive.records, key=lambda item: item.source_id),
        "node_attributes": sorted(archive.node_attributes, key=lambda item: item[0]),
        "surface_claims": sorted(archive.surface_claims, key=lambda item: item.claim_atom_id),
    })


def _symbol_rows(program: FieldProgramV2) -> tuple[str, ...]:
    values = {item.atom_id for item in program.atoms}
    values.update(item.factor_id for item in program.factors)
    values.update(item.source_key for item in program.provenances)
    values.update(item.scope_key for item in program.contexts)
    return tuple(sorted(values))


def _symbol_index(rows: tuple[str, ...]) -> dict[str, int]:
    return {value: index for index, value in enumerate(rows)}


def _vector_index(value: int | None) -> int:
    return _NONE if value is None else value


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def pack_tables(program: FieldProgramV2) -> dict[str, bytes]:
    """Return packed numeric tables. Strings are represented only by indexes."""
    symbols = _symbol_rows(program)
    symbol_index = _symbol_index(symbols)
    spaces = {space.space_id: index for index, space in enumerate(program.config.vector_spaces)}
    atoms = b"".join(
        _ATOM.pack(
            symbol_index[atom.atom_id], atom.kind_code, 0, atom.context_index,
            atom.provenance_index, symbol_index[atom.source_key], atom.source_start,
            atom.source_end, _vector_index(atom.canonical_vector), _vector_index(atom.occurrence_vector),
        )
        for atom in program.atoms
    )
    bindings = b"".join(
        _BINDING.pack(
            item.factor_index, item.role_code, item.ordinal, item.atom_index,
            _vector_index(item.role_vector), _vector_index(item.binding_vector), 0,
        )
        for item in program.bindings
    )
    factors = b"".join(
        _FACTOR.pack(
            symbol_index[item.factor_id], item.operator_code, 0, item.context_index,
            item.provenance_index, item.binding_start, item.binding_count, 0,
            _vector_index(item.operator_vector), item.region_index, item.base_weight,
            program.contexts[item.context_index].confidence,
            program.contexts[item.context_index].authority,
            program.contexts[item.context_index].priority, 0, 0,
        )
        for item in program.factors
    )
    contexts = b"".join(
        _CONTEXT.pack(
            symbol_index[item.scope_key], 1 if item.polarity == "positive" else 2, _MODALITIES.get(item.modality, 0),
            item.valid_from if item.valid_from is not None else -1,
            item.valid_to if item.valid_to is not None else -1,
            item.confidence, item.authority, item.priority, _vector_index(item.vector_ref), 0, 0,
        )
        for item in program.contexts
    )
    provenances = b"".join(
        _PROVENANCE.pack(
            symbol_index[item.source_key], item.source_start, item.source_end,
            bytes.fromhex(item.source_sha256),
        )
        for item in program.provenances
    )
    vectors = b"".join(
        _VECTOR.pack(
            index, spaces[item.space_id], item.row_index,
            bytes.fromhex(item.sidecar_sha256), bytes.fromhex(item.row_sha256),
        )
        for index, item in enumerate(program.vectors)
    )
    symbol_bytes = b"".join(hashlib.sha256(value.encode("utf-8")).digest() for value in symbols)
    vector_map = canonical_json({"vector_ids": [item.vector_id for item in program.vectors]}).encode("utf-8")
    return {
        "symbols": symbol_bytes,
        "symbol_map": canonical_json({"symbols": symbols}).encode("utf-8"),
        "vector_map": vector_map,
        "atoms": atoms,
        "factors": factors,
        "bindings": bindings,
        "contexts": contexts,
        "provenance": provenances,
        "vectors": vectors,
    }


def pack_program(root: Path, program: FieldProgramV2, archive: SourceArchive | None = None) -> FieldManifestV2:
    tables = pack_tables(program)
    table_hashes = tuple((name, sha256_bytes(payload)) for name, payload in sorted(tables.items()))
    row_sizes = {name: _table_struct(name).size for name in tables if name not in {"symbol_map", "vector_map"}}
    symbol_count = len(json.loads(tables["symbol_map"].decode("utf-8"))["symbols"])
    vector_count = len(json.loads(tables["vector_map"].decode("utf-8"))["vector_ids"])
    row_counts = tuple(
        (name, len(payload) // row_sizes[name] if name in row_sizes else (symbol_count if name == "symbol_map" else vector_count))
        for name, payload in sorted(tables.items())
    )
    manifest = FieldManifestV2(
        SCHEMA_VERSION,
        sha256_json(_config_semantics(program)),
        semantic_hash(program),
        artifact_hash(program),
        archive_hash(archive),
        table_hashes,
        row_counts,
        tuple((name, len(payload)) for name, payload in sorted(tables.items())),
    )
    root.mkdir(parents=True, exist_ok=True)
    for name, payload in tables.items():
        _write_atomic(root / f"{name}.bin", payload)
    if archive is not None:
        _write_atomic(root / "archive.json", canonical_json(archive).encode("utf-8"))
    _write_atomic(root / "manifest.json", canonical_json(manifest).encode("utf-8"))
    return manifest


def read_manifest(root: Path) -> FieldManifestV2:
    data = json.loads((root / "manifest.json").read_text())
    return FieldManifestV2(
        data["schema_version"], data["config_sha256"], data["semantic_sha256"],
        data["artifact_sha256"], data["archive_sha256"], tuple(tuple(item) for item in data["table_hashes"]),
        tuple((name, int(count)) for name, count in data["row_counts"]),
        tuple((name, int(count)) for name, count in data.get("byte_lengths", ())),
    )


def read_archive(root: Path) -> SourceArchive | None:
    """Read and validate the presentation-only source archive."""
    path = root / "archive.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    records = tuple(SourceArchiveRecord(
        item["source_id"], item["text"], item["source_sha256"], tuple(item.get("aliases", ()))
    ) for item in data.get("records", ()))
    attributes = tuple((item[0], tuple(tuple(pair) for pair in item[1])) for item in data.get("node_attributes", ()))
    claims = tuple(SurfaceClaimRecord(**item) for item in data.get("surface_claims", ()))
    return SourceArchive(records, attributes, claims, data.get("revision", "fieldir-archive/1"))


def verify_packed(root: Path, manifest: FieldManifestV2) -> None:
    for name, expected in manifest.table_hashes:
        path = root / f"{name}.bin"
        if not path.exists() or sha256_bytes(path.read_bytes()) != expected:
            raise ValueError("FIELD_TABLE_HASH_MISMATCH")
    expected_lengths = dict(manifest.byte_lengths)
    expected_rows = dict(manifest.row_counts)
    for name, length in expected_lengths.items():
        path = root / f"{name}.bin"
        if path.stat().st_size != length:
            raise ValueError("FIELD_TABLE_LENGTH_MISMATCH")
        if name not in expected_rows:
            raise ValueError("FIELD_ROW_COUNT_MISSING")
    if not (root / "manifest.json").exists():
        raise ValueError("FIELD_MANIFEST_MISSING")
    if manifest.archive_sha256 is not None:
        archive = read_archive(root)
        if archive is None or archive_hash(archive) != manifest.archive_sha256:
            raise ValueError("FIELD_ARCHIVE_HASH_MISMATCH")


def unpack_program(root: Path, config, archive: SourceArchive | None = None) -> FieldProgramV2:
    """Load numeric tables and reconstruct a canonical v2 program."""
    manifest = read_manifest(root)
    verify_packed(root, manifest)
    if sha256_json(_config_semantics(FieldProgramV2(config, (), (), (), (), ())) ) != manifest.config_sha256:
        raise ValueError("FIELD_CONFIG_HASH_MISMATCH")
    stored_archive = read_archive(root)
    if archive is None:
        archive = stored_archive
    elif stored_archive is not None and archive_hash(archive) != archive_hash(stored_archive):
        raise ValueError("FIELD_ARCHIVE_HASH_MISMATCH")
    symbols = tuple(json.loads((root / "symbol_map.bin").read_text(encoding="utf-8"))["symbols"])
    vector_ids = tuple(json.loads((root / "vector_map.bin").read_text(encoding="utf-8"))["vector_ids"])
    def symbol(index: int) -> str:
        try:
            return symbols[index]
        except IndexError as exc:
            raise ValueError("FIELD_SYMBOL_INDEX_MISMATCH") from exc
    atoms = []
    for row in _chunks((root / "atoms.bin").read_bytes(), _ATOM.size):
        identity, kind, _reserved, context, provenance, source, start, end, canonical, occurrence = _ATOM.unpack(row)
        atoms.append(AtomRecord(symbol(identity), kind, context, provenance, symbol(source), start, end, _optional(canonical), _optional(occurrence)))
    factors = []
    for row in _chunks((root / "factors.bin").read_bytes(), _FACTOR.size):
        identity, operator, _reserved, context, provenance, start, count, _reserved2, vector, region, weight_value, _confidence, _authority, _priority, _reserved3, _reserved4 = _FACTOR.unpack(row)
        factors.append(FactorRecord(symbol(identity), operator, context, provenance, start, count, weight_value, _optional(vector), region))
    bindings = []
    for row in _chunks((root / "bindings.bin").read_bytes(), _BINDING.size):
        factor, role, ordinal, atom, role_vector, binding_vector, _reserved = _BINDING.unpack(row)
        bindings.append(BindingRecord(factor, role, ordinal, atom, _optional(role_vector), _optional(binding_vector)))
    contexts = []
    for row in _chunks((root / "contexts.bin").read_bytes(), _CONTEXT.size):
        scope, polarity, modality, valid_from, valid_to, confidence, authority, priority, vector, _reserved, _reserved2 = _CONTEXT.unpack(row)
        modality_name = next((name for name, code in _MODALITIES.items() if code == modality), "asserted")
        contexts.append(ContextRecord(symbol(scope), "positive" if polarity == 1 else "negative", modality_name, None if valid_from < 0 else valid_from, None if valid_to < 0 else valid_to, confidence, authority, priority, _optional(vector)))
    provenances = []
    for row in _chunks((root / "provenance.bin").read_bytes(), _PROVENANCE.size):
        source, start, end, digest = _PROVENANCE.unpack(row)
        provenances.append(ProvenanceRecord(symbol(source), start, end, digest.hex()))
    spaces = {index: item.space_id for index, item in enumerate(config.vector_spaces)}
    vectors = []
    for row in _chunks((root / "vectors.bin").read_bytes(), _VECTOR.size):
        _index, space, row_index, sidecar, row_hash = _VECTOR.unpack(row)
        if _index >= len(vector_ids):
            raise ValueError("FIELD_VECTOR_ID_MISMATCH")
        vectors.append(VectorRef(vector_ids[_index], spaces[space], sidecar.hex(), row_index, row_hash.hex()))
    program = FieldProgramV2(config, tuple(atoms), tuple(factors), tuple(bindings), tuple(contexts), tuple(provenances), tuple(vectors))
    if semantic_hash(program) != manifest.semantic_sha256 or artifact_hash(program) != manifest.artifact_sha256:
        raise ValueError("FIELD_SEMANTIC_OR_ARTIFACT_HASH_MISMATCH")
    return program


def factor_record_size() -> int:
    return _FACTOR.size


def binding_record_size() -> int:
    return _BINDING.size


def _chunks(payload: bytes, width: int):
    if len(payload) % width:
        raise ValueError("FIELD_TABLE_ROW_ALIGNMENT")
    return (payload[index : index + width] for index in range(0, len(payload), width))


def _optional(value: int) -> int | None:
    return None if value == _NONE else value


def _table_struct(name: str) -> struct.Struct:
    return {
        "atoms": _ATOM,
        "factors": _FACTOR,
        "bindings": _BINDING,
        "contexts": _CONTEXT,
        "provenance": _PROVENANCE,
        "vectors": _VECTOR,
    }.get(name, struct.Struct("<32s"))
