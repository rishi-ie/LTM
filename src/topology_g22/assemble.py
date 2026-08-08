"""Fail-closed conversion of an accepted fragment into validated G1 objects."""
from __future__ import annotations

import re
from dataclasses import dataclass

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

from .schemas import FieldHandoff, SentenceFragment, TopologyDelta


@dataclass(frozen=True, slots=True)
class AssembledTopology:
    nodes: tuple[TopologyNode, ...]
    relations: tuple[RelationInstance, ...]
    operations: tuple[TopologyOperation, ...]
    delta: TopologyDelta
    handoff: FieldHandoff


def _provenance(fragment: SentenceFragment, start: int, end: int) -> Provenance:
    source = fragment.source
    return Provenance(source.source_id, source.source_start + start, source.source_start + end, source.source_hash)


def _node(fragment: SentenceFragment, span) -> TopologyNode:
    try:
        kind = NodeKind(span.node_kind)
    except ValueError as exc:
        raise ValueError(f"unsupported G1 node kind {span.node_kind}") from exc
    provenance = (_provenance(fragment, span.start, span.end),)
    payload = {
        "kind": kind.value,
        "text": span.text.casefold(),
        "scope": fragment.relations[0].scope_id if fragment.relations else "global",
        "validity": [None, None],
        "source": [provenance[0].source_id, provenance[0].source_span_start, provenance[0].source_span_end, provenance[0].source_hash],
    }
    node_id = semantic_id("g22-node", payload)
    return TopologyNode(
        node_id,
        2,
        kind,
        (("text", span.text),),
        payload["scope"],
        ValidityInterval(),
        provenance,
    )


def _relation(fragment: SentenceFragment, candidate, local_to_node: dict[str, str]) -> RelationInstance:
    if candidate.relation_type not in REGISTRY:
        raise ValueError("unknown relation")
    bindings = tuple(
        RoleBinding(role, local_to_node[local_id])
        for role, local_ids in candidate.role_local_ids
        for local_id in local_ids
    )
    provenance = (_provenance(fragment, 0, len(fragment.source.text)),)
    payload = {
        "relation_type": candidate.relation_type,
        "arguments": tuple((binding.role, binding.node_id) for binding in bindings),
        "scope": candidate.scope_id,
        "validity": (candidate.valid_from, candidate.valid_to),
        "source": provenance[0].source_hash,
    }
    return RelationInstance(
        semantic_id("g22-relation", payload),
        2,
        candidate.relation_type,
        bindings,
        candidate.scope_id,
        ValidityInterval(candidate.valid_from, candidate.valid_to),
        candidate.confidence,
        1.0,
        provenance,
    )


def render_fragment(fragment: SentenceFragment) -> str:
    """Canonical, deliberately small renderer used as a semantic round-trip check."""
    def render_relation(relation) -> str:
        bindings = ",".join(f"{role}={'|'.join(ids)}" for role, ids in relation.role_local_ids)
        by_id = {span.local_id: span.text for span in fragment.spans}
        arguments = " | ".join(by_id[local_id] for _role, ids in relation.role_local_ids for local_id in ids)
        return f"{relation.relation_type}({bindings}): {arguments}"

    relation_text = "; ".join(
        render_relation(relation) for relation in fragment.relations
    )
    return f"{fragment.disposition}: {relation_text}" if relation_text else fragment.disposition


def round_trip_similarity(original: str, rendered: str) -> float:
    # Controlled G2.2 uses opaque names and predicates. The check asks whether the canonical relation
    # rendering retained those topology addresses, not whether it reproduces English filler words.
    words = set(re.findall(r"[a-z0-9_-]+", original.casefold()))
    addresses = {word for word in words if "-" in word or len(word) >= 5}
    returned = set(re.findall(r"[a-z0-9_-]+", rendered.casefold()))
    return len(addresses & returned) / max(1, len(addresses))


def assemble(fragment: SentenceFragment) -> AssembledTopology | None:
    """Validate every object before making a delta; errors never produce partial writes."""
    if fragment.disposition != "accept":
        return None
    try:
        nodes = tuple(_node(fragment, span) for span in fragment.spans)
        local_to_node = {span.local_id: node.node_id for span, node in zip(fragment.spans, nodes)}
        relations = tuple(_relation(fragment, candidate, local_to_node) for candidate in fragment.relations)
        node_map = {node.node_id: node for node in nodes}
        for relation in relations:
            validate_relation(relation, node_map)
    except (KeyError, ValueError):
        return None
    provenance = (_provenance(fragment, 0, len(fragment.source.text)),)
    operations: list[TopologyOperation] = []
    for object_type, obj in (("insert_node", node) for node in nodes):
        op_id = semantic_id("g22-operation", {"type": object_type, "payload": canonical_json(obj)})
        operations.append(TopologyOperation(op_id, object_type, obj, provenance))
    for relation in relations:
        op_id = semantic_id("g22-operation", {"type": "insert_relation", "payload": canonical_json(relation)})
        operations.append(TopologyOperation(op_id, "insert_relation", relation, provenance))
    topology_hash = digest({"nodes": nodes, "relations": relations, "operations": tuple(operations)})
    delta = TopologyDelta(
        fragment.source.source_id,
        tuple(node.node_id for node in nodes),
        tuple(relation.relation_id for relation in relations),
        tuple(operation.operation_id for operation in operations),
        topology_hash,
    )
    field_operators = tuple(REGISTRY[relation.relation_type].field_operator for relation in relations)
    hard = tuple(
        relation.relation_id for relation in relations if REGISTRY[relation.relation_type].hard_or_soft == "hard"
    )
    handoff = FieldHandoff(
        topology_hash,
        tuple(relation.relation_id for relation in relations),
        field_operators,
        hard,
        tuple(item.source_hash for item in provenance),
    )
    return AssembledTopology(nodes, relations, tuple(operations), delta, handoff)
