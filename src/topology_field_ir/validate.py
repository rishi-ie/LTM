"""FieldIR validation, G1 projection, and exact execution bridge."""

from __future__ import annotations

import hashlib

from topology_g1.codec import canonical_json
from topology_g1.engine import execute
from topology_g1.registry import REGISTRY, validate_relation
from topology_g1.schemas import (
    Provenance,
    RelationInstance,
    RoleBinding,
    TopologyNode,
    ValidityInterval,
)

from .schemas import FieldProgram


class FieldIRValidationError(ValueError):
    pass


def registry_digest() -> str:
    return hashlib.sha256(canonical_json(REGISTRY).encode()).hexdigest()


def _provenance(atom_or_factor: object) -> tuple[Provenance, ...]:
    source = getattr(atom_or_factor, "source_id", None) or "fieldir"
    digest = atom_or_factor.provenance_sha256
    start = getattr(atom_or_factor, "source_start", 0)
    end = getattr(atom_or_factor, "source_end", start)
    return (Provenance(source, start, end, digest),)


def to_g1(program: FieldProgram) -> tuple[tuple[TopologyNode, ...], tuple[RelationInstance, ...]]:
    validate_program(program)
    nodes: list[TopologyNode] = []
    for atom in program.atoms:
        nodes.append(
            TopologyNode(
                atom.atom_id,
                2,
                __import__("topology_g1.schemas", fromlist=["NodeKind"]).NodeKind(atom.kind),
                tuple(sorted((("text", atom.occurrence_text),))),
                atom.context.scope_id,
                ValidityInterval(atom.context.valid_from, atom.context.valid_to),
                _provenance(atom),
            )
        )
    node_map = {node.node_id: node for node in nodes}
    relations: list[RelationInstance] = []
    for factor in program.factors:
        relation = RelationInstance(
            factor.factor_id,
            2,
            factor.relation_type,
            tuple(RoleBinding(role, atom_id) for role, atom_ids in factor.role_bindings for atom_id in atom_ids),
            factor.context.scope_id,
            ValidityInterval(factor.context.valid_from, factor.context.valid_to),
            factor.context.confidence,
            factor.context.authority,
            _provenance(factor),
        )
        validate_relation(relation, node_map)
        relations.append(relation)
    return tuple(nodes), tuple(relations)


def validate_program(program: FieldProgram) -> None:
    if program.registry_sha256 != registry_digest():
        raise FieldIRValidationError("G1 registry hash mismatch")
    spaces = {item.space_id: item for item in program.vector_spaces}
    atom_ids = {atom.atom_id for atom in program.atoms}
    for atom in program.atoms:
        for ref in (atom.canonical_vector, atom.occurrence_vector):
            if ref is not None and ref.space_id not in spaces:
                raise FieldIRValidationError("atom references unknown vector space")
    for factor in program.factors:
        if factor.relation_type not in REGISTRY:
            raise FieldIRValidationError("unknown factor operator")
        for _role, ids in factor.role_bindings:
            if not ids or any(atom_id not in atom_ids for atom_id in ids):
                raise FieldIRValidationError("factor references absent atom")
        for ref in (factor.operator_vector, *factor.role_vectors, *factor.binding_vectors):
            if ref is not None and ref.space_id not in spaces:
                raise FieldIRValidationError("factor references unknown vector space")
    try:
        to_g1_unchecked(program)
    except (KeyError, TypeError, ValueError) as exc:
        raise FieldIRValidationError(str(exc)) from exc


def to_g1_unchecked(program: FieldProgram) -> tuple[tuple[TopologyNode, ...], tuple[RelationInstance, ...]]:
    """Projection helper used to avoid validation recursion."""
    nodes: list[TopologyNode] = []
    for atom in program.atoms:
        nodes.append(TopologyNode(atom.atom_id, 2, __import__("topology_g1.schemas", fromlist=["NodeKind"]).NodeKind(atom.kind), (("text", atom.occurrence_text),), atom.context.scope_id, ValidityInterval(atom.context.valid_from, atom.context.valid_to), _provenance(atom)))
    node_map = {node.node_id: node for node in nodes}
    relations: list[RelationInstance] = []
    for factor in program.factors:
        relation = RelationInstance(factor.factor_id, 2, factor.relation_type, tuple(RoleBinding(role, atom_id) for role, ids in factor.role_bindings for atom_id in ids), factor.context.scope_id, ValidityInterval(factor.context.valid_from, factor.context.valid_to), factor.context.confidence, factor.context.authority, _provenance(factor))
        validate_relation(relation, node_map)
        relations.append(relation)
    return tuple(nodes), tuple(relations)


def execute_exact(program: FieldProgram, state):
    """Execute every FieldIR relation through the G1 exact engine."""
    nodes, relations = to_g1(program)
    node_map = {node.node_id: node for node in nodes}
    output = []
    current = state
    for relation in relations:
        derivations, contribution, current = execute(relation, node_map, current)
        output.append((derivations, contribution))
    return tuple(output), current
