"""G1-derived labels and legal typed candidate construction."""
from __future__ import annotations

from itertools import permutations, product

from topology_g1.registry import REGISTRY

from .schemas import SpanProposal

RELATION_LABELS = tuple(REGISTRY)
DISPOSITIONS = ("accept", "clarification_required", "quarantine")
NODE_KINDS = ("claim", "entity", "event", "scope", "preference", "question", "assistant_response")


def direction_for(relation_type: str) -> str:
    if relation_type in {"equals", "excludes"}:
        return "symmetric"
    if relation_type == "conjoins":
        return "multi_source_to_target"
    if relation_type == "after":
        return "arg2_to_arg1"
    return "arg1_to_arg2"


def enumerate_legal_candidates(
    spans: tuple[SpanProposal, ...], maximum: int = 48
) -> tuple[tuple[str, tuple[tuple[str, tuple[str, ...]], ...]], ...]:
    """Enumerate registry-authorized role assignments only; no free role labels exist."""
    primary: list[tuple[str, tuple[tuple[str, tuple[str, ...]], ...]]] = []
    alternatives: list[tuple[str, tuple[tuple[str, tuple[str, ...]], ...]]] = []
    for relation_type, spec in REGISTRY.items():
        role_slots: list[tuple[tuple[str, ...], ...]] = []
        possible = True
        for role in spec.roles:
            ids = tuple(span.local_id for span in spans if span.node_kind in {kind.value for kind in role.allowed_kinds})
            if len(ids) < role.minimum:
                possible = False
                break
            if role.minimum == 2:
                choices = tuple(tuple(pair) for pair in permutations(ids, 2))
            else:
                choices = tuple((value,) for value in ids)
            role_slots.append(choices)
        if not possible:
            continue
        relation_candidates: list[tuple[str, tuple[tuple[str, tuple[str, ...]], ...]]] = []
        for combination in product(*role_slots):
            flattened = tuple(item for values in combination for item in values)
            if len(flattened) != len(set(flattened)) and relation_type != "conjoins":
                continue
            bindings = tuple((role.name, tuple(values)) for role, values in zip(spec.roles, combination))
            relation_candidates.append((relation_type, bindings))
        if relation_candidates:
            primary.append(relation_candidates[0])
            alternatives.extend(relation_candidates[1:])
    return tuple((primary + alternatives)[:maximum])
