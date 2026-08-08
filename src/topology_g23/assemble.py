from __future__ import annotations

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

from .schemas import FieldHandoff, TopologyHypothesis, ValidatedSentenceIR


@dataclass(frozen=True, slots=True)
class Assembly:
    ir: ValidatedSentenceIR
    handoff: FieldHandoff


def _provenance(source, start: int, end: int) -> Provenance:
    return Provenance(source.source_id, source.source_start + start, source.source_start + end, source.source_hash)


def _node(source, span, scope: str) -> TopologyNode:
    kind = NodeKind(span.node_kind)
    provenance = (_provenance(source, span.start, span.end),)
    attributes = tuple(sorted((("text", span.text), ("start", span.start), ("end", span.end))))
    node_id = semantic_id("g23-node", {"kind": kind.value, "text": span.text.casefold(), "scope": scope, "source": source.source_hash, "start": span.start, "end": span.end})
    return TopologyNode(node_id, 2, kind, attributes, scope, ValidityInterval(), provenance)


def assemble(source, hypothesis: TopologyHypothesis) -> Assembly | None:
    if hypothesis.disposition != "accept" or not hypothesis.relations:
        return None
    try:
        scope = hypothesis.relations[0].scope_id or "global"
        nodes = tuple(_node(source, span, scope) for span in hypothesis.spans)
        local_to_node = {span.candidate_id: node.node_id for span, node in zip(hypothesis.spans, nodes)}
        source_provenance = (_provenance(source, 0, len(source.text)),)
        relations: list[RelationInstance] = []
        for candidate in hypothesis.relations:
            bindings = tuple(RoleBinding(role, local_to_node[local]) for role, ids in candidate.role_candidate_ids for local in ids)
            relation_payload = {
                "relation_type": candidate.relation_type,
                "arguments": tuple((item.role, item.node_id) for item in bindings),
                "scope": candidate.scope_id,
                "validity": (candidate.valid_from, candidate.valid_to),
                "source": source.source_hash,
            }
            relation = RelationInstance(
                semantic_id("g23-relation", relation_payload), 2, candidate.relation_type, bindings,
                candidate.scope_id, ValidityInterval(candidate.valid_from, candidate.valid_to),
                candidate.probability, 1.0, source_provenance,
            )
            validate_relation(relation, {node.node_id: node for node in nodes})
            relations.append(relation)
        operations: list[TopologyOperation] = []
        for node in nodes:
            operation_id = semantic_id("g23-operation", {"type": "insert_node", "payload": canonical_json(node)})
            operations.append(TopologyOperation(operation_id, "insert_node", node, source_provenance))
        for relation in relations:
            operation_id = semantic_id("g23-operation", {"type": "insert_relation", "payload": canonical_json(relation)})
            operations.append(TopologyOperation(operation_id, "insert_relation", relation, source_provenance))
        topology_hash = digest({"nodes": nodes, "relations": tuple(relations), "operations": tuple(operations)})
        ir = ValidatedSentenceIR(source.source_id, nodes, tuple(relations), tuple(operations), topology_hash)
        if not structural_round_trip(source, hypothesis, ir):
            return None
        handoff = FieldHandoff(
            topology_hash,
            tuple(relation.relation_id for relation in relations),
            tuple(REGISTRY[relation.relation_type].field_operator for relation in relations),
            tuple(relation.relation_id for relation in relations if REGISTRY[relation.relation_type].hard_or_soft == "hard"),
            tuple(item.source_hash for item in source_provenance),
        )
        return Assembly(ir, handoff)
    except (KeyError, ValueError, TypeError):
        return None


def structural_signature(hypothesis: TopologyHypothesis) -> tuple:
    return (
        tuple((span.node_kind, span.start, span.end, span.text) for span in hypothesis.spans),
        tuple((relation.relation_type, relation.role_candidate_ids, relation.scope_id, relation.valid_from, relation.valid_to) for relation in hypothesis.relations),
        hypothesis.disposition,
    )


def structural_round_trip(source, hypothesis: TopologyHypothesis, ir: ValidatedSentenceIR) -> bool:
    """Ensure canonical G1 assembly retained every semantic compiler field."""
    expected_spans = {
        (span.node_kind, span.text, span.start, span.end)
        for span in hypothesis.spans
    }
    actual_spans = {
        (
            node.kind.value,
            dict(node.attributes).get("text"),
            dict(node.attributes).get("start"),
            dict(node.attributes).get("end"),
        )
        for node in ir.nodes
    }
    if expected_spans != actual_spans:
        return False
    local_to_node = {
        span.candidate_id: node.node_id
        for span, node in zip(hypothesis.spans, ir.nodes)
    }
    expected_relations = {
        (
            relation.relation_type,
            tuple((role, local_to_node[item]) for role, values in relation.role_candidate_ids for item in values),
            relation.scope_id,
            relation.valid_from,
            relation.valid_to,
        )
        for relation in hypothesis.relations
    }
    actual_relations = {
        (
            relation.relation_type,
            tuple((binding.role, binding.node_id) for binding in relation.arguments),
            relation.scope_id,
            relation.validity.valid_from,
            relation.validity.valid_to,
        )
        for relation in ir.relations
    }
    return expected_relations == actual_relations and all(
        provenance.source_hash == source.source_hash
        for operation in ir.operations
        for provenance in operation.provenance
    )
