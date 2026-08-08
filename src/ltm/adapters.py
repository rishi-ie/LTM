"""Lossless intake adapters into the canonical numeric field program."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

from topology_field_ir.codec import write_vector_sidecar
from topology_field_ir.schemas import FieldProgram
from topology_g1.codec import canonical_json
from topology_g1.registry import REGISTRY
from topology_g1.schemas import (
    NodeKind,
    Provenance,
    RelationInstance,
    RoleBinding,
    TopologyNode,
    ValidityInterval,
)

from .schema import (
    AtomRecord,
    BindingRecord,
    ContextRecord,
    FactorRecord,
    FieldProgramV2,
    ProvenanceRecord,
    SourceArchive,
    SourceArchiveRecord,
    TopologyConfig,
    VectorRef,
    VectorSpaceSpec,
)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def registry_digest() -> str:
    return _digest(canonical_json(REGISTRY))


def config_from_g1(*, vector_spaces: tuple[VectorSpaceSpec, ...] = ()) -> TopologyConfig:
    """Derive all structural codes from the authoritative G1 registry."""
    if not vector_spaces:
        zero = "0" * 64
        vector_spaces = tuple(
            VectorSpaceSpec(name, "unbound", zero, dimension)
            for name, dimension in (("content", 384), ("operator", 128), ("role", 64), ("context", 64), ("binding", 256))
        )
    relations = tuple((name, index) for index, name in enumerate(sorted(REGISTRY), 1))
    roles = tuple((name, index) for index, name in enumerate(sorted({role.name for spec in REGISTRY.values() for role in spec.roles}), 1))
    kinds = tuple((name.value, index) for index, name in enumerate(sorted(NodeKind, key=lambda item: item.value), 1))
    return TopologyConfig("ltm-v1", registry_digest(), relations, roles, kinds, vector_spaces)


def _context_index(contexts: list[ContextRecord], value: ContextRecord) -> int:
    try:
        return contexts.index(value)
    except ValueError:
        contexts.append(value)
        return len(contexts) - 1


def _provenance_index(provenances: list[ProvenanceRecord], value: ProvenanceRecord) -> int:
    try:
        return provenances.index(value)
    except ValueError:
        provenances.append(value)
        return len(provenances) - 1


def _node_context(node: TopologyNode) -> ContextRecord:
    return ContextRecord(
        node.scope_id,
        str(node.attr("polarity", "positive")),
        str(node.attr("modality", "asserted")),
        node.validity.valid_from,
        node.validity.valid_to,
        1.0,
        1.0,
    )


def _node_provenance(node: TopologyNode) -> ProvenanceRecord:
    item = node.provenance[0]
    return ProvenanceRecord(item.source_id, item.source_span_start, item.source_span_end, item.source_hash)


def _relation_context(relation: RelationInstance) -> ContextRecord:
    return ContextRecord(
        relation.scope_id,
        "positive",
        "asserted",
        relation.validity.valid_from,
        relation.validity.valid_to,
        relation.confidence,
        relation.authority,
    )


def from_g1(
    nodes: tuple[TopologyNode, ...],
    relations: tuple[RelationInstance, ...],
    config: TopologyConfig | None = None,
) -> tuple[FieldProgramV2, SourceArchive]:
    """Convert exact G1 objects to text-free numeric tables."""
    config = config or config_from_g1()
    kind_codes = config.node_kind_map
    relation_codes = config.relation_map
    role_codes = config.role_map
    contexts: list[ContextRecord] = []
    provenances: list[ProvenanceRecord] = []
    atoms: list[AtomRecord] = []
    archive_records: dict[str, SourceArchiveRecord] = {}
    archive_attributes: list[tuple[str, tuple[tuple[str, object], ...]]] = []
    for node in nodes:
        context_index = _context_index(contexts, _node_context(node))
        provenance_index = _provenance_index(provenances, _node_provenance(node))
        atoms.append(AtomRecord(
            node.node_id, kind_codes[node.kind.value], context_index, provenance_index,
            node.provenance[0].source_id, node.provenance[0].source_span_start,
            node.provenance[0].source_span_end,
        ))
        source = node.provenance[0]
        if _digest(source.source_id) == source.source_hash:
            archive_records.setdefault(source.source_id, SourceArchiveRecord(source.source_id, source.source_id, source.source_hash))
        archive_attributes.append((node.node_id, node.attributes))
    bindings: list[BindingRecord] = []
    factors: list[FactorRecord] = []
    for factor_index, relation in enumerate(relations):
        context_index = _context_index(contexts, _relation_context(relation))
        provenance_index = _provenance_index(provenances, ProvenanceRecord(
            relation.provenance[0].source_id,
            relation.provenance[0].source_span_start,
            relation.provenance[0].source_span_end,
            relation.provenance[0].source_hash,
        ))
        start = len(bindings)
        for ordinal, argument in enumerate(relation.arguments):
            bindings.append(BindingRecord(
                factor_index, role_codes[argument.role], ordinal, next(index for index, atom in enumerate(atoms) if atom.atom_id == argument.node_id),
            ))
        factors.append(FactorRecord(
            relation.relation_id, relation_codes[relation.relation_type], context_index,
            provenance_index, start, len(bindings) - start, 1.0,
        ))
    program = FieldProgramV2(config, tuple(atoms), tuple(factors), tuple(bindings), tuple(contexts), tuple(provenances))
    archive = SourceArchive(tuple(archive_records.values()), tuple(archive_attributes))
    return program, archive


def to_g1(program: FieldProgramV2, archive: SourceArchive | None = None) -> tuple[tuple[TopologyNode, ...], tuple[RelationInstance, ...]]:
    """Project numeric tables back to G1, using archive data only for attributes."""
    from topology_g1.registry import validate_relation

    kind_by_code = {code: name for name, code in program.config.node_kind_codes}
    role_by_code = {code: name for name, code in program.config.role_codes}
    archived = dict(archive.node_attributes) if archive else {}
    nodes: list[TopologyNode] = []
    for index, atom in enumerate(program.atoms):
        context = program.contexts[atom.context_index]
        provenance = program.provenances[atom.provenance_index]
        nodes.append(TopologyNode(
            atom.atom_id, 2, NodeKind(kind_by_code[atom.kind_code]), archived.get(atom.atom_id, ()),
            context.scope_key, ValidityInterval(context.valid_from, context.valid_to),
            (Provenance(provenance.source_key, provenance.source_start, provenance.source_end, provenance.source_sha256),),
        ))
    node_map = {node.node_id: node for node in nodes}
    relations: list[RelationInstance] = []
    for factor in program.factors:
        context = program.contexts[factor.context_index]
        provenance = program.provenances[factor.provenance_index]
        selected = program.bindings[factor.binding_start : factor.binding_start + factor.binding_count]
        relation = RelationInstance(
            factor.factor_id, 2, next(name for name, code in program.config.relation_codes if code == factor.operator_code),
            tuple(RoleBinding(role_by_code[item.role_code], program.atoms[item.atom_index].atom_id) for item in selected),
            context.scope_key, ValidityInterval(context.valid_from, context.valid_to), round(context.confidence, 7), round(context.authority, 7),
            (Provenance(provenance.source_key, provenance.source_start, provenance.source_end, provenance.source_sha256),),
        )
        validate_relation(relation, node_map)
        relations.append(relation)
    return tuple(nodes), tuple(relations)


def _refs_for_vectors(root: Path, space_id: str, rows: list[tuple[float, ...]], dimension: int) -> tuple[VectorRef, ...]:
    if not rows:
        return ()
    sidecar_hash, row_hashes = write_vector_sidecar(root / f"{space_id}.ltmf", rows, dimension)
    return tuple(VectorRef(f"{space_id}:{index}", space_id, sidecar_hash, index, row_hash) for index, row_hash in enumerate(row_hashes))


def from_fieldir_v1(program: FieldProgram, config: TopologyConfig | None = None) -> tuple[FieldProgramV2, SourceArchive]:
    """Migrate the source-facing FieldIR v1 graph while retaining vector refs."""
    nodes, relations = __import__("topology_field_ir.validate", fromlist=["to_g1"]).to_g1(program)
    if config is None:
        spaces = tuple(
            VectorSpaceSpec(space.space_id, space.revision, space.encoder_sha256, space.dimension, space.metric, space.normalized, space.dtype)
            for space in program.vector_spaces
        )
        config = config_from_g1(vector_spaces=spaces)
    migrated, archive = from_g1(tuple(nodes), tuple(relations), config)
    refs: list[VectorRef] = []
    ref_index: dict[VectorRef, int] = {}
    for atom in program.atoms:
        for ref in (atom.canonical_vector, atom.occurrence_vector):
            if ref is not None and ref not in ref_index:
                ref_index[ref] = len(refs); refs.append(VectorRef(ref.vector_id, ref.space_id, ref.sidecar_sha256, ref.row_index, ref.row_sha256))
    for factor in program.factors:
        for ref in (factor.operator_vector, *factor.role_vectors, *factor.binding_vectors):
            if ref is not None and ref not in ref_index:
                ref_index[ref] = len(refs); refs.append(VectorRef(ref.vector_id, ref.space_id, ref.sidecar_sha256, ref.row_index, ref.row_sha256))
    atoms = tuple(replace(atom, canonical_vector=ref_index.get(source.canonical_vector), occurrence_vector=ref_index.get(source.occurrence_vector)) for atom, source in zip(migrated.atoms, program.atoms))
    factors = []
    bindings = list(migrated.bindings)
    for index, (factor, source) in enumerate(zip(migrated.factors, program.factors)):
        factors.append(replace(factor, operator_vector=ref_index.get(source.operator_vector)))
        role_refs = iter(source.role_vectors)
        binding_refs = iter(source.binding_vectors)
        for binding_index in range(factor.binding_start, factor.binding_start + factor.binding_count):
            bindings[binding_index] = replace(bindings[binding_index], role_vector=ref_index.get(next(role_refs, None)), binding_vector=ref_index.get(next(binding_refs, None)))
    return replace(migrated, atoms=atoms, factors=tuple(factors), bindings=tuple(bindings), vectors=tuple(refs)), archive


def from_g25_handoff(handoff, source_sha256: str, vector_root: Path) -> tuple[FieldProgramV2, SourceArchive]:
    """Convert an accepted G2.5 handoff; the source digest is mandatory."""
    if len(source_sha256) != 64:
        raise ValueError("SOURCE_HASH_MISMATCH")
    operations = tuple(item.payload for item in handoff.g1_operations)
    nodes = tuple(item for item in operations if isinstance(item, TopologyNode))
    relations = tuple(item for item in operations if isinstance(item, RelationInstance))
    program, archive = from_g1(nodes, relations)
    content_rows = [atom.canonical_vector for atom in handoff.content_atoms] + [atom.occurrence_vector for atom in handoff.content_atoms]
    content_refs = _refs_for_vectors(vector_root, "content", content_rows, 384)
    operator_rows = [factor.operator_vector for factor in handoff.topology_factors]
    operator_refs = _refs_for_vectors(vector_root, "operator", operator_rows, 128)
    role_rows = [placement.role_vector for factor in handoff.topology_factors for placement in factor.role_placements]
    role_refs = _refs_for_vectors(vector_root, "role", role_rows, 64)
    binding_rows = [row for factor in handoff.topology_factors for row in factor.binding_vectors]
    binding_refs = _refs_for_vectors(vector_root, "binding", binding_rows, 256)
    context_rows = [factor.context.vector for factor in handoff.topology_factors]
    context_refs = _refs_for_vectors(vector_root, "context", context_rows, 64)
    refs = content_refs + operator_refs + role_refs + binding_refs + context_refs
    ref_offset = {ref.vector_id: index for index, ref in enumerate(refs)}
    atom_updates = []
    for atom in program.atoms:
        source = next((value for value in handoff.content_atoms if value.node_kind == next(name for name, code in program.config.node_kind_codes if code == atom.kind_code) and value.source_start == atom.source_start and value.source_end == atom.source_end), None)
        if source is None:
            atom_updates.append(atom)
            continue
        position = handoff.content_atoms.index(source)
        atom_updates.append(replace(atom, canonical_vector=ref_offset[f"content:{position}"], occurrence_vector=ref_offset[f"content:{len(handoff.content_atoms) + position}"]))
    factor_updates = []
    context_updates = list(program.contexts)
    context_ref_by_pair: dict[tuple[int, int], int] = {}
    binding_updates = list(program.bindings)
    for factor_index, factor in enumerate(program.factors):
        source = handoff.topology_factors[factor_index]
        factor_position = handoff.topology_factors.index(source)
        context_ref = ref_offset[f"context:{factor_position}"]
        context_key = (factor.context_index, context_ref)
        context_index = context_ref_by_pair.get(context_key)
        if context_index is None:
            context_index = len(context_updates)
            context_ref_by_pair[context_key] = context_index
            context_updates.append(replace(program.contexts[factor.context_index], vector_ref=context_ref))
        factor_updates.append(
            replace(
                factor,
                context_index=context_index,
                operator_vector=ref_offset[f"operator:{factor_position}"],
            )
        )
        for ordinal in range(factor.binding_count):
            binding = binding_updates[factor.binding_start + ordinal]
            role_position = sum(len(value.role_placements) for value in handoff.topology_factors[:factor_position]) + ordinal
            binding_position = sum(len(value.binding_vectors) for value in handoff.topology_factors[:factor_position]) + ordinal
            binding_updates[factor.binding_start + ordinal] = replace(binding, role_vector=ref_offset[f"role:{role_position}"], binding_vector=ref_offset[f"binding:{binding_position}"])
    return replace(
        program,
        atoms=tuple(atom_updates),
        factors=tuple(factor_updates),
        bindings=tuple(binding_updates),
        contexts=tuple(context_updates),
        vectors=refs,
    ), archive
