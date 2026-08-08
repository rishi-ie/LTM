"""Lossless conversion between atom programs, G1 objects and tensor IR."""

from __future__ import annotations

from topology_g1.codec import canonical_json, digest, semantic_id
from topology_g1.registry import REGISTRY, validate_relation
from topology_g1.schemas import (
    NodeKind,
    Provenance,
    RelationInstance,
    RoleBinding,
    TopologyNode,
    TopologyOperation,
    ValidityInterval,
)

from .registry import node_kind_index, relation_index
from .schemas import (
    GroundedAtom,
    OperatorHypothesis,
    SentenceSource,
    TensorTopologyIR,
    TopologyProgram,
    ValidatedProgram,
)


def atom_signature(atom: GroundedAtom) -> tuple[str, int, int, str, str, int | None, int | None, str, str]:
    return (
        atom.node_kind,
        atom.source_start,
        atom.source_end,
        atom.text,
        atom.scope_id,
        atom.valid_from,
        atom.valid_to,
        atom.polarity,
        atom.modality,
    )


def _provenance(source: SentenceSource, start: int, end: int) -> Provenance:
    return Provenance(source.source_id, source.source_start + start, source.source_start + end, source.source_hash)


def _node(source: SentenceSource, atom: GroundedAtom) -> TopologyNode:
    kind = NodeKind(atom.node_kind)
    attributes = tuple(
        sorted(
            (
                ("text", atom.text),
                ("start", atom.source_start),
                ("end", atom.source_end),
                ("polarity", atom.polarity),
                ("modality", atom.modality),
            )
        )
    )
    node_id = semantic_id(
        "g24-node",
        {
            "kind": atom.node_kind,
            "text": atom.text.casefold(),
            "source": source.source_hash,
            "span": (atom.source_start, atom.source_end),
            "scope": atom.scope_id,
            "validity": (atom.valid_from, atom.valid_to),
            "polarity": atom.polarity,
            "modality": atom.modality,
        },
    )
    return TopologyNode(
        node_id,
        2,
        kind,
        attributes,
        atom.scope_id,
        ValidityInterval(atom.valid_from, atom.valid_to),
        (_provenance(source, atom.source_start, atom.source_end),),
    )


def _relation(
    source: SentenceSource,
    hypothesis: OperatorHypothesis,
    local_to_node: dict[str, str],
) -> RelationInstance:
    bindings = tuple(
        RoleBinding(role, local_to_node[local])
        for role, local_ids in hypothesis.role_bindings
        for local in local_ids
    )
    payload = {
        "relation_type": hypothesis.relation_type,
        "arguments": tuple((item.role, item.node_id) for item in bindings),
        "scope": hypothesis.scope_id,
        "validity": (hypothesis.valid_from, hypothesis.valid_to),
        "source": source.source_hash,
    }
    return RelationInstance(
        semantic_id("g24-relation", payload),
        2,
        hypothesis.relation_type,
        bindings,
        hypothesis.scope_id,
        ValidityInterval(hypothesis.valid_from, hypothesis.valid_to),
        hypothesis.probability,
        1.0,
        (_provenance(source, 0, len(source.text)),),
    )


def program_signature(program: TopologyProgram) -> tuple:
    atoms = {atom.local_id: atom_signature(atom) for atom in program.atoms}
    relations = []
    for relation in program.operators:
        bindings = tuple(
            (role, tuple(atoms[local] for local in local_ids))
            for role, local_ids in relation.role_bindings
        )
        relations.append((relation.relation_type, bindings, relation.scope_id, relation.valid_from, relation.valid_to))
    return (program.disposition, tuple(sorted(atoms.values())), tuple(sorted(relations)))


def _tensor_ir(program: TopologyProgram, nodes: tuple[TopologyNode, ...], relations: tuple[RelationInstance, ...]) -> TensorTopologyIR:
    ordered = tuple(sorted(zip(program.atoms, nodes), key=lambda item: item[1].node_id))
    local_to_index = {atom.local_id: index for index, (atom, _node) in enumerate(ordered)}
    atom_signatures = tuple(
        (atom.node_kind, atom.source_start, atom.source_end, atom.text, atom.scope_id)
        for atom, _node in ordered
    )
    relation_signatures = tuple(
        (
            relation_type.relation_type,
            tuple((role, tuple(local_to_index[local] for local in values)) for role, values in relation_type.role_bindings),
            relation_type.scope_id,
            relation_type.valid_from,
            relation_type.valid_to,
        )
        for relation_type in program.operators
    )
    role_incidence = tuple(
        tuple((role, index) for role, indices in signature[1] for index in indices)
        for signature in relation_signatures
    )
    field_operator_ids = tuple(REGISTRY[relation.relation_type].field_operator for relation in relations)
    hard_mask = tuple(REGISTRY[relation.relation_type].hard_or_soft == "hard" for relation in relations)
    payload = {
        "nodes": tuple(node.node_id for _atom, node in ordered),
        "atom_signatures": atom_signatures,
        "relations": relation_signatures,
        "fields": field_operator_ids,
    }
    return TensorTopologyIR(
        tuple(node.node_id for _atom, node in ordered),
        tuple(node_kind_index(atom.node_kind) for atom, _node in ordered),
        tuple(atom.semantic_vector for atom, _node in ordered),
        tuple(relation_index(relation.relation_type) for relation in relations),
        role_incidence,
        hard_mask,
        field_operator_ids,
        atom_signatures,
        relation_signatures,
        tuple(sorted({provenance.source_id for node in nodes for provenance in node.provenance})),
        digest(payload),
    )


def tensor_signature(tensor: TensorTopologyIR) -> tuple:
    return (
        tuple(sorted(tensor.atom_signatures)),
        tuple(sorted(tensor.relation_signatures)),
    )


def assemble_program(source: SentenceSource, program: TopologyProgram) -> ValidatedProgram | None:
    """Atomically build G1 objects; malformed programs never partially escape."""
    if program.source_id != source.source_id or program.disposition != "accept":
        return None
    try:
        nodes = tuple(_node(source, atom) for atom in program.atoms)
        local_to_node = {atom.local_id: node.node_id for atom, node in zip(program.atoms, nodes)}
        relations = tuple(_relation(source, item, local_to_node) for item in program.operators)
        node_map = {node.node_id: node for node in nodes}
        for relation in relations:
            validate_relation(relation, node_map)
        source_provenance = (_provenance(source, 0, len(source.text)),)
        operations = tuple(
            [
                TopologyOperation(
                    semantic_id("g24-operation", {"type": "insert_node", "payload": canonical_json(node)}),
                    "insert_node",
                    node,
                    source_provenance,
                )
                for node in nodes
            ]
            + [
                TopologyOperation(
                    semantic_id("g24-operation", {"type": "insert_relation", "payload": canonical_json(relation)}),
                    "insert_relation",
                    relation,
                    source_provenance,
                )
                for relation in relations
            ]
        )
        topology_hash = digest({"nodes": nodes, "relations": relations, "operations": operations})
        tensor = _tensor_ir(program, nodes, relations)
        if tensor_signature(tensor) != (
            tuple(sorted((item.node_kind, item.source_start, item.source_end, item.text, item.scope_id) for item in program.atoms)),
            tuple(sorted(tensor.relation_signatures)),
        ):
            return None
        return ValidatedProgram(program, nodes, relations, operations, tensor, topology_hash)
    except (KeyError, TypeError, ValueError):
        return None
