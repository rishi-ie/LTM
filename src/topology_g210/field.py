"""Atomic G1, FieldIR, and text-free numeric handoff for accepted cells."""

from __future__ import annotations

import hashlib
from pathlib import Path

from topology_field_ir import (
    FieldContext,
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
from topology_field_ir.validate import registry_digest
from topology_field_r1 import from_fieldir, numeric_digest, text_free_g1
from topology_g1.schemas import TopologyOperation

from .schemas import PublicAtom
from .topology import CELL_BY_ID


def _ref(space: str, digest: str, rows: tuple[str, ...], index: int, name: str) -> VectorRef:
    return VectorRef(name, space, digest, index, rows[index])


def build_program(source_id: str, source_hash: str, atoms: tuple[PublicAtom, ...], cell_id: str, atom_ids: tuple[str, str], scope_id: str, modality: str, content_rows: tuple[tuple[float, ...], ...], behavioral: tuple[float, ...], sidecar_root: Path) -> tuple[FieldProgram, tuple[TopologyOperation, ...], str]:
    """Build first, validate all representations, then return a complete handoff."""
    cell = CELL_BY_ID[cell_id]
    context = FieldContext(scope_id, "positive", modality, None, None, 1.0, 1.0)
    sidecar_root.mkdir(parents=True, exist_ok=True)
    content_path = sidecar_root / f"{source_id}.content.vec"
    behavior_path = sidecar_root / f"{source_id}.behavior.vec"
    content_sha, content_hashes = write_vector_sidecar(content_path, content_rows, 384)
    behavior_sha, behavior_hashes = write_vector_sidecar(behavior_path, (behavioral,), len(behavioral))
    spaces = (
        VectorSpaceSpec("g210-content", "g210-r1", hashlib.sha256(b"all-MiniLM-L6-v2").hexdigest(), 384),
        VectorSpaceSpec("g210-behavior", "g210-r1", hashlib.sha256(b"behavioral-probes-v1").hexdigest(), len(behavioral), normalized=False),
    )
    field_atoms = tuple(
        GoldenAtom(atom.atom_id, atom.kind, atom.text, atom.text, source_id, atom.start, atom.end, context, atom.provenance_sha256, _ref("g210-content", content_sha, content_hashes, index, f"{source_id}:atom:{atom.atom_id}"), _ref("g210-content", content_sha, content_hashes, index, f"{source_id}:occurrence:{atom.atom_id}"))
        for index, atom in enumerate(atoms)
    )
    factor_id = "g210-factor-" + hashlib.sha256(repr((source_id, cell_id, atom_ids)).encode()).hexdigest()[:24]
    factor = TypedFactor(
        factor_id,
        cell.relation_type,
        tuple((role, (atom_id,)) for role, atom_id in zip(cell.roles, atom_ids, strict=True)),
        context,
        source_hash,
        1.0,
        _ref("g210-behavior", behavior_sha, behavior_hashes, 0, f"{source_id}:behavior"),
    )
    program = FieldProgram(source_id, registry_digest(), spaces, field_atoms, (factor,))
    validate_program(program)
    verify_vector_artifacts(program, {content_sha: content_path, behavior_sha: behavior_path})
    nodes, relations = to_g1(program)
    # Numeric conversion validates that text can be external to active execution.
    numeric, _archive = from_fieldir(program)
    numeric_nodes, numeric_relations = text_free_g1(numeric)
    if len(nodes) != len(numeric_nodes) or len(relations) != len(numeric_relations):
        raise ValueError("numeric handoff differs from G1")
    operations = tuple(
        [TopologyOperation(f"{source_id}:node:{index}", "upsert_node", node, node.provenance) for index, node in enumerate(nodes)]
        + [TopologyOperation(f"{source_id}:relation", "upsert_relation", relations[0], relations[0].provenance)]
    )
    return program, operations, numeric_digest(numeric)
