"""Atomic G1/FieldIR construction; continuous rows never authorize factors."""

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

from .decoder import GraphCandidate


def _write_sidecar(path: Path, rows: tuple[tuple[float, ...], ...], dimension: int) -> tuple[str, tuple[str, ...], Path]:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(descriptor)
    temporary_path = Path(temporary)
    try:
        digest, rows_hash = write_vector_sidecar(temporary_path, rows, dimension)
        temporary_path.replace(path)
        return digest, rows_hash, path
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _ref(space: str, digest: str, hashes: tuple[str, ...], row: int, owner: str) -> VectorRef:
    return VectorRef(f"{owner}:{row}", space, digest, row, hashes[row])


def build_program(*, program_id: str, atoms: tuple[GoldenAtom, ...], graph: GraphCandidate, context, bank, content_rows: tuple[tuple[float, ...], ...], operator_coordinate: tuple[float, ...], role_rows: tuple[tuple[float, ...], ...], binding_rows: tuple[tuple[float, ...], ...], delta_rows: tuple[tuple[float, ...], ...], sidecar_dir: Path) -> tuple[FieldProgram | None, tuple[TopologyOperation, ...], str | None, str | None, str | None]:
    """Build all artifacts first, then return an all-or-nothing handoff."""
    if graph.disposition != "accept":
        return None, (), None, None, None
    if len(content_rows) != len(atoms):
        raise ValueError("content rows and atoms differ")
    provenance = atoms[0].provenance_sha256 if atoms else "0" * 64
    content_sha, content_hashes, content_path = _write_sidecar(sidecar_dir / f"{program_id}.content.vec", content_rows, 384)
    operator_sha, operator_hashes, operator_path = _write_sidecar(sidecar_dir / f"{program_id}.operator.vec", (operator_coordinate,), 18)
    role_sha, role_hashes, role_path = _write_sidecar(sidecar_dir / f"{program_id}.role.vec", role_rows or ((1.0,) + (0.0,) * 63,), 64)
    binding_sha, binding_hashes, binding_path = _write_sidecar(sidecar_dir / f"{program_id}.binding.vec", binding_rows or ((1.0,) + (0.0,) * 127,), 128)
    delta_sha, _delta_hashes, _delta_path = _write_sidecar(sidecar_dir / f"{program_id}.delta.vec", delta_rows or ((0.0,) * 192,), 192)
    spaces = (
        VectorSpaceSpec("g29-content", bank.revision, bank.bank_hash, 384),
        VectorSpaceSpec("g29-operator-coordinate", bank.revision, bank.bank_hash, 18, normalized=False),
        VectorSpaceSpec("g29-role", bank.revision, bank.bank_hash, 64),
        VectorSpaceSpec("g29-binding", bank.revision, bank.bank_hash, 128),
    )
    vector_atoms = tuple(GoldenAtom(atom.atom_id, atom.kind, atom.canonical_text, atom.occurrence_text, atom.source_id, atom.source_start, atom.source_end, atom.context, atom.provenance_sha256, _ref("g29-content", content_sha, content_hashes, index, f"{program_id}:canonical"), _ref("g29-content", content_sha, content_hashes, index, f"{program_id}:occurrence")) for index, atom in enumerate(atoms))
    definitions = {item.relation_type: item for item in bank.operators}
    factors = []
    row = 0
    for relation in graph.relations:
        count = sum(len(atom_ids) for _role, atom_ids in relation.role_bindings)
        factor_id = "g29-factor-" + hashlib.sha256(repr((program_id, relation)).encode()).hexdigest()[:24]
        factors.append(TypedFactor(factor_id, relation.relation_type, relation.role_bindings, context, provenance, definitions[relation.relation_type].base_field_weight, _ref("g29-operator-coordinate", operator_sha, operator_hashes, 0, f"{factor_id}:operator"), tuple(_ref("g29-role", role_sha, role_hashes, (row + offset) % len(role_hashes), f"{factor_id}:role") for offset in range(count)), tuple(_ref("g29-binding", binding_sha, binding_hashes, (row + offset) % len(binding_hashes), f"{factor_id}:binding") for offset in range(count))))
        row += count
    program = FieldProgram(program_id, registry_digest(), spaces, vector_atoms, tuple(factors))
    validate_program(program)
    verify_vector_artifacts(program, {content_sha: content_path, operator_sha: operator_path, role_sha: role_path, binding_sha: binding_path})
    nodes, relations = to_g1(program)
    operations = tuple([TopologyOperation(f"{program_id}:node:{index}", "upsert_node", node, node.provenance) for index, node in enumerate(nodes)] + [TopologyOperation(f"{program_id}:relation:{index}", "upsert_relation", relation, relation.provenance) for index, relation in enumerate(relations)])
    # Delta rows are compiler-only diagnostics; their digest is deliberately
    # separate from the G1/FieldIR semantic signature.
    return program, operations, semantic_digest(program), artifact_digest(program), delta_sha
