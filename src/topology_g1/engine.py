from __future__ import annotations

from dataclasses import replace

from .registry import validate_relation
from .schemas import (
    ConflictRecord,
    Derivation,
    ExecutionState,
    FieldContribution,
    HardObligation,
    RelationInstance,
    SchemaError,
    TopologyNode,
    TypedMessage,
    VerificationRecord,
)


def _scope_ok(relation: RelationInstance, state: ExecutionState) -> bool:
    return relation.scope_id in ("global", state.scope_id)


def _applicable(relation: RelationInstance, state: ExecutionState) -> bool:
    return _scope_ok(relation, state) and relation.validity.valid_from is not None or _scope_ok(relation, state)


def _message(relation: RelationInstance, kind: str, ids: tuple[str, ...], value: float) -> TypedMessage:
    return TypedMessage(relation.relation_id, kind, ids, value)


def _obligation(relation: RelationInstance, code: str, ids: tuple[str, ...]) -> HardObligation:
    return HardObligation(relation.relation_id, code, ids)


def _residual(relation: RelationInstance, state: ExecutionState) -> float:
    r = relation.relation_type
    if r in ("implies", "fictional_rule"):
        return max(0.0, state.value(relation.role_ids("premise")[0]) - state.value(relation.role_ids("conclusion")[0])) ** 2
    if r == "conjoins":
        premises = relation.role_ids("premise")
        activation = max(0.0, sum(state.value(node_id) for node_id in premises) - (len(premises) - 1))
        return max(0.0, activation - state.value(relation.role_ids("conclusion")[0])) ** 2
    if r == "requires":
        return max(0.0, state.value(relation.role_ids("dependent")[0]) - state.value(relation.role_ids("prerequisite")[0])) ** 2
    if r == "excludes":
        return max(0.0, state.value(relation.role_ids("left")[0]) + state.value(relation.role_ids("right")[0]) - 1) ** 2
    if r == "equals":
        return (state.value(relation.role_ids("left")[0]) - state.value(relation.role_ids("right")[0])) ** 2
    if r in ("before", "after"):
        first = state.value(relation.role_ids("first")[0])
        second = state.value(relation.role_ids("second")[0])
        if r == "after":
            first, second = second, first
        return max(0.0, first - second) ** 2
    return 0.0


def execute(
    relation: RelationInstance,
    nodes: dict[str, TopologyNode],
    state: ExecutionState,
) -> tuple[tuple[Derivation, ...], FieldContribution, ExecutionState]:
    validate_relation(relation, nodes)
    if not _scope_ok(relation, state):
        contribution = FieldContribution(relation.relation_id, 0.0, (), (_obligation(relation, "SCOPE_VIOLATION", (relation.scope_id,)),))
        return (), contribution, state
    residual = _residual(relation, state)
    derivations: tuple[Derivation, ...] = ()
    messages: tuple[TypedMessage, ...] = ()
    obligations: tuple[HardObligation, ...] = ()
    updated = state
    r = relation.relation_type
    if r in ("implies", "fictional_rule") or r == "conjoins":
        premises = relation.role_ids("premise")
        conclusion = relation.role_ids("conclusion")[0]
        if all(item in state.active_claims for item in premises):
            derivations = (Derivation(conclusion, relation.relation_id, premises, relation.scope_id, relation.provenance),)
    elif r == "requires":
        dependent = relation.role_ids("dependent")[0]
        prerequisite = relation.role_ids("prerequisite")[0]
        if dependent in state.active_claims and prerequisite not in state.active_claims:
            obligations = (_obligation(relation, "MISSING_PREMISE", (dependent, prerequisite)),)
    elif r == "excludes":
        pair = relation.role_ids("left") + relation.role_ids("right")
        if all(item in state.active_claims for item in pair):
            conflict = ConflictRecord(relation.relation_id, pair)
            updated = replace(state, conflicts=tuple(sorted(state.conflicts + (conflict,), key=lambda item: item.relation_id)))
    elif r == "equals":
        left, right = relation.role_ids("left")[0], relation.role_ids("right")[0]
        if state.value(left) == state.value(right):
            derivations = (
                Derivation(right, relation.relation_id, (left,), relation.scope_id, relation.provenance),
                Derivation(left, relation.relation_id, (right,), relation.scope_id, relation.provenance),
            )
    elif r == "supersedes":
        older, newer = relation.role_ids("older")[0], relation.role_ids("newer")[0]
        if newer in state.active_claims:
            updated = replace(state, inactive_claims=frozenset(set(state.inactive_claims) | {older}))
    elif r in ("supports", "opposes", "causes_hypothetically", "uncertainty"):
        source_role = "evidence" if r in ("supports", "opposes") else "cause" if r == "causes_hypothetically" else "source"
        target_role = "claim" if r in ("supports", "opposes", "uncertainty") else "effect"
        kind = "support" if r == "supports" else "opposition" if r == "opposes" else "causal_hypothesis" if r == "causes_hypothetically" else "uncertainty"
        messages = (_message(relation, kind, relation.role_ids(source_role) + relation.role_ids(target_role), relation.confidence * relation.authority),)
    elif r == "prefers":
        preference = relation.role_ids("preference")[0]
        updated = replace(state, response_constraints=tuple(sorted(set(state.response_constraints) | {preference})))
    elif r == "refers_to":
        mention, entity = relation.role_ids("mention")[0], relation.role_ids("entity")[0]
        updated = replace(state, reference_bindings=tuple(sorted(set(state.reference_bindings) | {(mention, entity)})))
    elif r == "scoped_to":
        if relation.scope_id != state.scope_id:
            obligations = (_obligation(relation, "SCOPE_VIOLATION", relation.role_ids("subject")),)
    elif r in ("before", "after"):
        if residual > 0:
            obligations = (_obligation(relation, "TEMPORAL_VIOLATION", relation.role_ids("first") + relation.role_ids("second")),)
    elif r in ("assistant_derived_from", "derived_from"):
        source_role = "evidence" if r == "assistant_derived_from" else "source"
        target_role = "response" if r == "assistant_derived_from" else "derived"
        messages = (_message(relation, "provenance", relation.role_ids(source_role) + relation.role_ids(target_role), 1.0),)
    return derivations, FieldContribution(relation.relation_id, residual, messages, obligations), updated


def verify_derivation(
    derivation: Derivation,
    relation: RelationInstance,
    nodes: dict[str, TopologyNode],
    state: ExecutionState,
) -> VerificationRecord:
    try:
        validate_relation(relation, nodes)
    except SchemaError as exc:
        return VerificationRecord(False, (), (), exc.code)
    if not _scope_ok(relation, state):
        return VerificationRecord(False, (), (), "SCOPE_VIOLATION")
    if derivation.relation_id != relation.relation_id or derivation.scope_id != relation.scope_id:
        return VerificationRecord(False, (), (), "REVERSED_RELATION")
    if derivation.provenance != relation.provenance:
        return VerificationRecord(False, (), (), "SOURCE_HASH_MISMATCH")
    r = relation.relation_type
    if r in ("implies", "fictional_rule", "conjoins"):
        expected_premises = relation.role_ids("premise")
        expected_conclusion = relation.role_ids("conclusion")[0]
        if derivation.premise_ids != expected_premises or derivation.conclusion_id != expected_conclusion:
            return VerificationRecord(False, (), (), "REVERSED_RELATION")
        if not all(item in state.active_claims for item in expected_premises):
            return VerificationRecord(False, (), (), "MISSING_PREMISE")
    elif r == "equals":
        left, right = relation.role_ids("left")[0], relation.role_ids("right")[0]
        permitted = {(left, right), (right, left)}
        if (derivation.premise_ids[0] if len(derivation.premise_ids) == 1 else None, derivation.conclusion_id) not in permitted or state.value(left) != state.value(right):
            return VerificationRecord(False, (), (), "MISSING_PREMISE")
    else:
        return VerificationRecord(False, (), (), "INVALID_DERIVATION")
    return VerificationRecord(True, tuple(item.role for item in relation.arguments), tuple(item.source_id for item in relation.provenance))
