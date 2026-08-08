"""Atomic G1 and FieldIR handoff with vector sidecars."""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

from topology_field_ir import (
    FieldProgram,
    GoldenAtom,
    TypedFactor,
    VectorRef,
    VectorSpaceSpec,
    to_g1,
    validate_program,
    verify_vector_artifacts,
    write_vector_sidecar,
)
from topology_field_ir.codec import artifact_digest, semantic_digest
from topology_field_ir.validate import registry_digest
from topology_g1.schemas import TopologyOperation

from .atom_bank import AtomBankManifest
from .decoder import GraphCandidate


def _atomic_sidecar(path: Path, rows: tuple[tuple[float, ...], ...], dimension: int) -> tuple[str, tuple[str, ...], Path]:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    temporary_path = Path(temporary)
    try:
        digest, row_digests = write_vector_sidecar(temporary_path, rows, dimension)
        temporary_path.replace(path)
        return digest, row_digests, path
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _ref(space: str, sidecar: str, rows: tuple[str, ...], index: int, prefix: str) -> VectorRef:
    return VectorRef(f"{prefix}:{index}", space, sidecar, index, rows[index])


def build_program(
    *,
    program_id: str,
    atoms: tuple[GoldenAtom, ...],
    graph: GraphCandidate,
    context,
    bank: AtomBankManifest,
    content_rows: tuple[tuple[float, ...], ...],
    operator_coordinate: tuple[float, ...],
    role_rows: tuple[tuple[float, ...], ...],
    binding_rows: tuple[tuple[float, ...], ...],
    sidecar_dir: Path,
) -> tuple[FieldProgram | None, tuple[TopologyOperation, ...], str | None, str | None]:
    if graph.disposition != "accept":
        return None, (), None, None
    provenance = atoms[0].provenance_sha256 if atoms else "0" * 64
    if len(content_rows) != len(atoms):
        raise ValueError("content vector rows differ from atoms")
    content_sha, content_hashes, content_path = _atomic_sidecar(sidecar_dir / f"{program_id}.content.vec", content_rows, 384)
    operator_sha, operator_hashes, operator_path = _atomic_sidecar(sidecar_dir / f"{program_id}.operator.vec", (operator_coordinate,), 18)
    role_sha, role_hashes, role_path = _atomic_sidecar(sidecar_dir / f"{program_id}.role.vec", role_rows or ((1.0,) + (0.0,) * 63,), 64)
    binding_sha, binding_hashes, binding_path = _atomic_sidecar(sidecar_dir / f"{program_id}.binding.vec", binding_rows or ((1.0,) + (0.0,) * 127,), 128)
    spaces = (
        VectorSpaceSpec("g28-content", bank.revision, bank.bank_hash, 384),
        VectorSpaceSpec("g28-operator-coordinate", bank.revision, bank.bank_hash, 18, normalized=False),
        VectorSpaceSpec("g28-role", bank.revision, bank.bank_hash, 64),
        VectorSpaceSpec("g28-binding", bank.revision, bank.bank_hash, 128),
    )
    vector_atoms = tuple(
        GoldenAtom(
            atom.atom_id, atom.kind, atom.canonical_text, atom.occurrence_text, atom.source_id,
            atom.source_start, atom.source_end, atom.context, atom.provenance_sha256,
            _ref("g28-content", content_sha, content_hashes, index, f"{program_id}:canonical"),
            _ref("g28-content", content_sha, content_hashes, index, f"{program_id}:occurrence"),
        )
        for index, atom in enumerate(atoms)
    )
    by_relation = {item.relation_type: item for item in bank.operators}
    row_index = 0
    factors = []
    for relation in graph.relations:
        binding_count = sum(len(ids) for _role, ids in relation.role_bindings)
        factor_id = "g28-factor-" + hashlib.sha256(repr((program_id, relation)).encode()).hexdigest()[:24]
        factors.append(
            TypedFactor(
                factor_id, relation.relation_type, relation.role_bindings, context, provenance,
                by_relation[relation.relation_type].base_field_weight,
                _ref("g28-operator-coordinate", operator_sha, operator_hashes, 0, f"{factor_id}:operator"),
                tuple(_ref("g28-role", role_sha, role_hashes, (row_index + offset) % len(role_hashes), f"{factor_id}:role") for offset in range(binding_count)),
                tuple(_ref("g28-binding", binding_sha, binding_hashes, (row_index + offset) % len(binding_hashes), f"{factor_id}:binding") for offset in range(binding_count)),
            )
        )
        row_index += binding_count
    program = FieldProgram(program_id, registry_digest(), spaces, vector_atoms, tuple(factors))
    validate_program(program)
    sidecars = {content_sha: content_path, operator_sha: operator_path, role_sha: role_path, binding_sha: binding_path}
    verify_vector_artifacts(program, sidecars)
    nodes, relations = to_g1(program)
    operations = tuple(
        [TopologyOperation(f"{program_id}:node:{index}", "upsert_node", node, node.provenance) for index, node in enumerate(nodes)]
        + [TopologyOperation(f"{program_id}:relation:{index}", "upsert_relation", relation, relation.provenance) for index, relation in enumerate(relations)]
    )
    return program, operations, semantic_digest(program), artifact_digest(program)
