from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from .codec import semantic_id, source_hash
from .schemas import (
    ExecutionState,
    NodeKind,
    Provenance,
    RelationInstance,
    RoleBinding,
    TopologyNode,
    ValidityInterval,
)

FAMILIES = (
    "implies", "conjoins", "requires", "excludes", "equals", "before", "supersedes", "supports",
    "prefers", "refers_to", "scoped_to", "fictional_rule", "causes_hypothetically", "uncertainty",
    "assistant_derived_from", "derived_from",
)


@dataclass(frozen=True, slots=True)
class Fixture:
    fixture_id: str
    split: Literal["development", "locked"]
    family: str
    variant: int
    nodes: tuple[TopologyNode, ...]
    relation: RelationInstance
    state: ExecutionState
    expected: str
    invalid_code: str | None = None
    migration: bool = False


def _prov(tag: str) -> Provenance:
    return Provenance(f"source-{tag}", 0, len(tag), source_hash(f"source-{tag}"))


def _node(tag: str, kind: NodeKind, scope: str, value: float = 1.0) -> TopologyNode:
    attributes = (("label", tag), ("value", value))
    node_id = semantic_id("node", {"tag": tag, "kind": kind.value, "scope": scope})
    return TopologyNode(node_id, 2, kind, attributes, scope, ValidityInterval(0, 100), (_prov(tag),))


def _relation(tag: str, relation_type: str, args: tuple[RoleBinding, ...], scope: str) -> RelationInstance:
    relation_id = semantic_id("relation", {"tag": tag, "type": relation_type, "args": tuple((x.role, x.node_id) for x in args), "scope": scope})
    return RelationInstance(relation_id, 2, relation_type, args, scope, ValidityInterval(0, 100), 0.8, 0.9, (_prov(f"rel-{tag}"),))


def _family_case(split: str, family: str, variant: int) -> Fixture:
    tag = f"{split}-{family}-{variant}"
    scope = "fictional" if family == "fictional_rule" else "global"
    claim_a = _node(f"{tag}-a", NodeKind.CLAIM, scope, 1.0)
    claim_b = _node(f"{tag}-b", NodeKind.CLAIM, scope, 1.0)
    claim_c = _node(f"{tag}-c", NodeKind.CLAIM, scope, 1.0)
    entity = _node(f"{tag}-entity", NodeKind.ENTITY, scope)
    mention = _node(f"{tag}-mention", NodeKind.QUESTION, scope)
    preference = _node(f"{tag}-preference", NodeKind.PREFERENCE, scope)
    response = _node(f"{tag}-response", NodeKind.GOAL, scope)
    event_a = _node(f"{tag}-event-a", NodeKind.EVENT, scope, 1.0)
    event_b = _node(f"{tag}-event-b", NodeKind.EVENT, scope, 2.0)
    scope_node = _node(f"{tag}-scope", NodeKind.SCOPE, scope)
    assistant = _node(f"{tag}-assistant", NodeKind.ASSISTANT_RESPONSE, scope)
    mapping = {
        "implies": ((RoleBinding("premise", claim_a.node_id), RoleBinding("conclusion", claim_b.node_id)), (claim_a, claim_b), "derive"),
        "conjoins": ((RoleBinding("premise", claim_a.node_id), RoleBinding("premise", claim_b.node_id), RoleBinding("conclusion", claim_c.node_id)), (claim_a, claim_b, claim_c), "derive"),
        "requires": ((RoleBinding("dependent", claim_a.node_id), RoleBinding("prerequisite", claim_b.node_id)), (claim_a, claim_b), "obligation"),
        "excludes": ((RoleBinding("left", claim_a.node_id), RoleBinding("right", claim_b.node_id)), (claim_a, claim_b), "conflict"),
        "equals": ((RoleBinding("left", claim_a.node_id), RoleBinding("right", claim_b.node_id)), (claim_a, claim_b), "derive"),
        "before": ((RoleBinding("first", event_a.node_id), RoleBinding("second", event_b.node_id)), (event_a, event_b), "temporal"),
        "supersedes": ((RoleBinding("older", claim_a.node_id), RoleBinding("newer", claim_b.node_id)), (claim_a, claim_b), "supersede"),
        "supports": ((RoleBinding("evidence", claim_a.node_id), RoleBinding("claim", claim_b.node_id)), (claim_a, claim_b), "message"),
        "prefers": ((RoleBinding("preference", preference.node_id), RoleBinding("response", response.node_id)), (preference, response), "preference"),
        "refers_to": ((RoleBinding("mention", mention.node_id), RoleBinding("entity", entity.node_id)), (mention, entity), "reference"),
        "scoped_to": ((RoleBinding("subject", claim_a.node_id), RoleBinding("scope", scope_node.node_id)), (claim_a, scope_node), "scope"),
        "fictional_rule": ((RoleBinding("premise", claim_a.node_id), RoleBinding("conclusion", claim_b.node_id), RoleBinding("scope", scope_node.node_id)), (claim_a, claim_b, scope_node), "derive"),
        "causes_hypothetically": ((RoleBinding("cause", claim_a.node_id), RoleBinding("effect", claim_b.node_id)), (claim_a, claim_b), "message"),
        "uncertainty": ((RoleBinding("source", claim_a.node_id), RoleBinding("claim", claim_b.node_id)), (claim_a, claim_b), "message"),
        "assistant_derived_from": ((RoleBinding("response", assistant.node_id), RoleBinding("evidence", claim_a.node_id)), (assistant, claim_a), "message"),
        "derived_from": ((RoleBinding("derived", claim_a.node_id), RoleBinding("source", claim_b.node_id)), (claim_a, claim_b), "message"),
    }
    arguments, nodes, expected = mapping[family]
    relation = _relation(tag, family, arguments, scope)
    active = {claim_a.node_id, claim_b.node_id}
    if family == "conjoins":
        active.add(claim_b.node_id)
    if family == "requires":
        active.discard(claim_b.node_id)
    if family == "supersedes":
        active.add(claim_b.node_id)
    values = ((claim_a.node_id, 1.0), (claim_b.node_id, 1.0), (event_a.node_id, 1.0), (event_b.node_id, 2.0))
    state = ExecutionState(frozenset(active), numeric_values=values, scope_id=scope)
    if variant in (1, 4, 5):
        state = replace(state, active_claims=frozenset({claim_a.node_id}), numeric_values=((claim_a.node_id, 1.0), (claim_b.node_id, 0.0), (event_a.node_id, 2.0), (event_b.node_id, 1.0)))
    if variant == 2:
        state = replace(state, scope_id="outside" if scope == "fictional" else "global")
    invalid_code = None
    if variant == 6:
        relation = replace(relation, arguments=relation.arguments[1:])
        invalid_code = "MISSING_ROLE"
    elif variant == 7:
        bad = _node(f"{tag}-bad", NodeKind.ENTITY, scope)
        relation = replace(relation, arguments=(RoleBinding(relation.arguments[0].role, bad.node_id),) + relation.arguments[1:])
        nodes = tuple(nodes) + (bad,)
        invalid_code = "INVALID_ARGUMENT_TYPE"
    elif variant == 8:
        relation = replace(relation, relation_type="unknown_relation")
        invalid_code = "UNKNOWN_RELATION"
    return Fixture(f"{split}-{family}-{variant}", split, family, variant, tuple(nodes), relation, state, expected, invalid_code, variant == 9)


def fixtures(split: str) -> tuple[Fixture, ...]:
    return tuple(_family_case(split, family, variant) for family in FAMILIES for variant in range(10) if (variant < 5) == (split == "development"))


def all_fixtures() -> tuple[Fixture, ...]:
    return fixtures("development") + fixtures("locked-final")


def legacy_node_v1(node: TopologyNode) -> dict[str, object]:
    return {
        "node_id": node.node_id,
        "schema_version": 1,
        "kind": node.kind.value,
        "attributes": list(node.attributes),
        "scope": node.scope_id,
        "valid_from": node.validity.valid_from,
        "valid_to": node.validity.valid_to,
        "source_id": node.provenance[0].source_id,
        "source_span_start": node.provenance[0].source_span_start,
        "source_span_end": node.provenance[0].source_span_end,
        "source_hash": node.provenance[0].source_hash,
    }
