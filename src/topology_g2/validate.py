from __future__ import annotations

import json
import math
from typing import Any

from topology_g1.codec import semantic_id
from topology_g1.registry import validate_relation
from topology_g1.schemas import (
    NodeKind,
    Provenance,
    RelationInstance,
    RoleBinding,
    SchemaError,
    TopologyNode,
    TopologyOperation,
    ValidityInterval,
)

from .schemas import CandidateIR, ContextSnapshot, SourceRecord, ValidatedIR
from .serde import candidate_from_dict


def _json(text: str) -> dict[str, Any]:
    start = text.find("{")
    if start < 0:
        raise SchemaError("INVALID_JSON", "no JSON object")
    try:
        # Greedy decoding can occasionally continue with a repeated answer.
        # Decode exactly the first complete object; any surrounding prose is
        # still harmless because the object itself must pass strict checks.
        value, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError as exc:
        raise SchemaError("INVALID_JSON", str(exc)) from exc
    if not isinstance(value, dict):
        raise SchemaError("INVALID_JSON", "object required")
    return value


def parse_candidate(text: str) -> CandidateIR:
    try:
        candidate = candidate_from_dict(_json(text))
    except (TypeError, ValueError, KeyError) as exc:
        raise SchemaError("INVALID_JSON", str(exc)) from exc
    if candidate.disposition not in ("accept", "clarification_required", "quarantine"):
        raise SchemaError("INVALID_DISPOSITION", candidate.disposition)
    for obj in candidate.objects:
        if not obj.local_id or obj.node_kind not in {kind.value for kind in NodeKind}:
            raise SchemaError("INVALID_OBJECT", obj.local_id)
        if not math.isfinite(obj.confidence) or not 0 <= obj.confidence <= 1:
            raise SchemaError("INVALID_WEIGHT", obj.local_id)
        _span(obj.source_quote, obj.occurrence, "")
    return candidate


def _span(quote: str, occurrence: int, text: str) -> tuple[int, int]:
    if occurrence < 0 or not quote:
        raise SchemaError("INVALID_SOURCE_SPAN", "quote and occurrence required")
    if not text:
        return (0, 0)
    start = -1
    for _ in range(occurrence + 1):
        start = text.find(quote, start + 1)
        if start < 0:
            raise SchemaError("INVALID_SOURCE_SPAN", quote)
    return start, start + len(quote)


def _provenance(source: SourceRecord, quote: str, occurrence: int) -> Provenance:
    start, end = _span(quote, occurrence, source.text)
    return Provenance(source.source_id, start, end, source.source_hash)


def _resolve_entity(value: str | None, context: ContextSnapshot) -> str | None:
    if value is None:
        return None
    lowered = value.casefold().strip()
    candidates = [entity.entity_id for entity in context.entities if lowered in {alias.casefold() for alias in entity.aliases}]
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        raise SchemaError("AMBIGUOUS_REFERENCE", value)
    return value.casefold().strip().replace(" ", "-")


def validate_candidate(candidate: CandidateIR, source: SourceRecord, context: ContextSnapshot) -> ValidatedIR:
    if candidate.disposition != "accept":
        if candidate.objects or candidate.relations:
            raise SchemaError("INVALID_DISPOSITION", "non-accept disposition must not write topology")
        return ValidatedIR(candidate.disposition, (), (), (), "ambiguous" if candidate.disposition == "clarification_required" else None, "unsupported" if candidate.disposition == "quarantine" else None)
    nodes: list[TopologyNode] = []
    local: dict[str, TopologyNode] = {}
    for obj in candidate.objects:
        if obj.local_id in local:
            raise SchemaError("DUPLICATE_LOCAL_ID", obj.local_id)
        provenance = _provenance(source, obj.source_quote, obj.occurrence)
        subject = _resolve_entity(obj.subject, context)
        attributes = tuple(sorted((key, value) for key, value in {
            "subject": subject,
            "predicate": obj.predicate.casefold().strip() if obj.predicate else None,
            "object": obj.object.casefold().strip() if obj.object else None,
            "polarity": obj.polarity,
            "modality": obj.modality,
        }.items()))
        node_id = semantic_id("g2-node", {"kind": obj.node_kind, "attributes": attributes, "scope": "global", "source": source.source_id, "span": (provenance.source_span_start, provenance.source_span_end)})
        node = TopologyNode(node_id, 2, NodeKind(obj.node_kind), attributes, "global", ValidityInterval(0, 100), (provenance,))
        nodes.append(node)
        local[obj.local_id] = node
    relations: list[RelationInstance] = []
    for index, item in enumerate(candidate.relations):
        if not math.isfinite(item.confidence) or not 0 <= item.confidence <= 1:
            raise SchemaError("INVALID_WEIGHT", item.relation_type)
        args = []
        for role, local_ids in item.arguments:
            for local_id in local_ids:
                if local_id not in local:
                    raise SchemaError("UNKNOWN_LOCAL_ID", local_id)
                args.append(RoleBinding(role, local[local_id].node_id))
        scope = "fictional" if item.scope_name.casefold() in {"fictional", "aster realm"} else "global"
        relation_id = semantic_id("g2-relation", {"type": item.relation_type, "args": tuple((arg.role, arg.node_id) for arg in args), "scope": scope, "source": source.source_id, "index": index})
        provenance = _provenance(source, candidate.objects[0].source_quote, candidate.objects[0].occurrence) if candidate.objects else Provenance(source.source_id, 0, len(source.text), source.source_hash)
        relation = RelationInstance(relation_id, 2, item.relation_type, tuple(args), scope, ValidityInterval(item.valid_from, item.valid_to), item.confidence, item.confidence, (provenance,))
        validate_relation(relation, {node.node_id: node for node in nodes})
        relations.append(relation)
    operations = tuple(
        TopologyOperation(semantic_id("g2-operation", {"node": node.node_id}), "insert_node", node, node.provenance) for node in nodes
    ) + tuple(
        TopologyOperation(semantic_id("g2-operation", {"relation": relation.relation_id}), "insert_relation", relation, relation.provenance) for relation in relations
    )
    return ValidatedIR("accept", tuple(nodes), tuple(relations), operations, None, None)


def validate_text(text: str, source: SourceRecord, context: ContextSnapshot) -> tuple[CandidateIR, ValidatedIR]:
    candidate = parse_candidate(text)
    return candidate, validate_candidate(candidate, source, context)
