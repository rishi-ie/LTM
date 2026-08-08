from __future__ import annotations

from itertools import permutations, product

from topology_g1.registry import REGISTRY

from .schemas import TypedSpanCandidate

RELATION_LABELS = tuple(REGISTRY)
DISPOSITION_LABELS = ("accept", "clarification_required", "quarantine")
SCOPE_LABELS = ("global", "conversation_local", "fictional", "hypothetical", "temporally_bounded")
NODE_KINDS = tuple(kind.value for spec in REGISTRY.values() for role in spec.roles for kind in role.allowed_kinds)
NODE_KINDS = tuple(dict.fromkeys(NODE_KINDS))


def direction_for(relation_type: str) -> str:
    if relation_type in {"equals", "excludes"}:
        return "symmetric"
    if relation_type == "conjoins":
        return "multi_source_to_target"
    if relation_type == "after":
        return "arg2_to_arg1"
    return "arg1_to_arg2"


def enumerate_legal_candidates(
    spans: tuple[TypedSpanCandidate, ...],
    maximum: int = 96,
    per_relation: int = 4,
) -> tuple[tuple[str, tuple[tuple[str, tuple[str, ...]], ...], float], ...]:
    """Enumerate only registry-legal graphs without relation-order pruning.

    The old prototype globally sorted candidates, which meant a high-scoring
    relation could erase another legal relation before the graph scorer saw it.
    Retaining a small, deterministic quota per relation makes candidate recall
    measurable and keeps the 96-candidate ceiling bounded.
    """
    by_relation: dict[str, list[tuple[str, tuple[tuple[str, tuple[str, ...]], ...], float]]] = {
        relation: [] for relation in RELATION_LABELS
    }
    for relation_type, spec in REGISTRY.items():
        choices: list[tuple[tuple[str, ...], ...]] = []
        possible = True
        for role in spec.roles:
            allowed = {kind.value for kind in role.allowed_kinds}
            ids = tuple(span.candidate_id for span in spans if span.node_kind in allowed)
            if len(ids) < role.minimum:
                possible = False
                break
            if role.minimum == 2:
                role_choices = tuple(tuple(pair) for pair in permutations(ids, 2))
            else:
                role_choices = tuple((item,) for item in ids)
            choices.append(role_choices)
        if not possible:
            continue
        for combination in product(*choices):
            flattened = tuple(value for values in combination for value in values)
            if relation_type != "conjoins" and len(flattened) != len(set(flattened)):
                continue
            bindings = tuple((role.name, tuple(values)) for role, values in zip(spec.roles, combination))
            score = sum(next(span.span_probability for span in spans if span.candidate_id == item) for item in flattened)
            by_relation[relation_type].append((relation_type, bindings, score))
    candidates: list[tuple[str, tuple[tuple[str, tuple[str, ...]], ...], float]] = []
    for relation_type in RELATION_LABELS:
        candidates.extend(
            sorted(by_relation[relation_type], key=lambda item: (-item[2], item[1]))[:per_relation]
        )
    candidates.sort(key=lambda item: (-item[2], item[0], item[1]))
    return tuple(candidates[:maximum])
