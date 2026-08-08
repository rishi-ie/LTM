"""G1-constrained complete graph candidates and tiny deterministic set matching."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, permutations, product

from topology_g1.registry import REGISTRY


@dataclass(frozen=True, slots=True)
class RelationCandidate:
    relation_type: str
    role_bindings: tuple[tuple[str, tuple[str, ...]], ...]


@dataclass(frozen=True, slots=True)
class GraphCandidate:
    relations: tuple[RelationCandidate, ...]
    disposition: str

    @property
    def relation_types(self) -> tuple[str, ...]:
        return tuple(item.relation_type for item in self.relations)

    @property
    def role_bindings(self) -> tuple[tuple[str, tuple[str, ...]], ...]:
        return tuple((f"{item.relation_type}:{role}", ids) for item in self.relations for role, ids in item.role_bindings)


def _relation_candidates(atoms: tuple[tuple[str, str], ...], relation: str, limit: int = 32) -> tuple[RelationCandidate, ...]:
    spec = REGISTRY[relation]
    slots = [role for role in spec.roles for _ in range(role.minimum)]
    eligible = [[item for item in atoms if item[1] in {kind.value for kind in role.allowed_kinds}] for role in slots]
    if any(not values for values in eligible):
        return ()
    result = []
    for selected in product(*eligible):
        ids = tuple(item[0] for item in selected)
        if len(set(ids)) != len(ids):
            continue
        grouped: dict[str, list[str]] = {}
        for role, (atom_id, _kind) in zip(slots, selected, strict=True):
            grouped.setdefault(role.name, []).append(atom_id)
        result.append(RelationCandidate(relation, tuple((role.name, tuple(grouped[role.name])) for role in spec.roles)))
        if len(result) == limit:
            break
    return tuple(result)


def enumerate_graphs(atoms: tuple[tuple[str, str], ...], maximum: int = 512) -> tuple[GraphCandidate, ...]:
    by_relation = {relation: _relation_candidates(atoms, relation) for relation in REGISTRY}
    output = [GraphCandidate((), "clarification_required"), GraphCandidate((), "quarantine")]
    output.extend(GraphCandidate((candidate,), "accept") for relation in REGISTRY for candidate in by_relation[relation])
    for left, right in combinations(REGISTRY, 2):
        for first in by_relation[left][:4]:
            for second in by_relation[right][:4]:
                if first.role_bindings != second.role_bindings:
                    output.append(GraphCandidate((first, second), "accept"))
                if len(output) >= maximum:
                    return tuple(output)
    return tuple(output[:maximum])


def gold_graph(relations: tuple[str, ...], bindings: tuple[tuple[str, tuple[str, ...]], ...], disposition: str) -> GraphCandidate:
    if disposition != "accept":
        return GraphCandidate((), disposition)
    bound = dict(bindings)
    return GraphCandidate(tuple(RelationCandidate(relation, tuple((role.name, bound[f"{relation}:{role.name}"]) for role in REGISTRY[relation].roles)) for relation in relations), "accept")


def minimum_matching_cost(costs: tuple[tuple[float, ...], ...]) -> tuple[int, ...]:
    """Exact matching for at most three instances; no extra dependency required."""
    if not costs:
        return ()
    width = len(costs[0])
    if len(costs) > width or width > 3:
        raise ValueError("G2.9 matching is bounded to three relation instances")
    return min(permutations(range(width), len(costs)), key=lambda pairing: (sum(costs[row][column] for row, column in enumerate(pairing)), pairing))
