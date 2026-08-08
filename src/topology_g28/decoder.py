"""G1-constrained complete graph candidates for G2.8."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, product

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
    eligible = [
        [(atom_id, kind) for atom_id, kind in atoms if kind in {allowed.value for allowed in role.allowed_kinds}]
        for role in slots
    ]
    if any(not items for items in eligible):
        return ()
    candidates = []
    for selection in product(*eligible):
        atom_ids = tuple(item[0] for item in selection)
        if len(set(atom_ids)) != len(atom_ids):
            continue
        grouped: dict[str, list[str]] = {}
        for role, (atom_id, _kind) in zip(slots, selection, strict=True):
            grouped.setdefault(role.name, []).append(atom_id)
        candidates.append(RelationCandidate(relation, tuple((role.name, tuple(grouped[role.name])) for role in spec.roles)))
        if len(candidates) >= limit:
            break
    return tuple(candidates)


def enumerate_graphs(atoms: tuple[tuple[str, str], ...], *, maximum: int = 512) -> tuple[GraphCandidate, ...]:
    """Enumerate legal one/two-relation graphs plus safe null actions.

    Per-relation enumeration is bounded before graph composition; every G1
    relation is represented before the global cap is applied.
    """
    by_relation = {relation: _relation_candidates(atoms, relation) for relation in REGISTRY}
    output = [GraphCandidate((), "clarification_required"), GraphCandidate((), "quarantine")]
    singles = [candidate for relation in REGISTRY for candidate in by_relation[relation]]
    output.extend(GraphCandidate((candidate,), "accept") for candidate in singles)
    for left, right in combinations(REGISTRY, 2):
        for first in by_relation[left][:4]:
            for second in by_relation[right][:4]:
                if first.role_bindings == second.role_bindings:
                    continue
                output.append(GraphCandidate((first, second), "accept"))
                if len(output) >= maximum:
                    return tuple(output)
    return tuple(output[:maximum])


def gold_graph(relation_types: tuple[str, ...], role_bindings: tuple[tuple[str, tuple[str, ...]], ...], disposition: str) -> GraphCandidate:
    if disposition != "accept":
        return GraphCandidate((), disposition)
    relations = []
    bindings = dict(role_bindings)
    for relation in relation_types:
        relations.append(RelationCandidate(relation, tuple((role.name, bindings[f"{relation}:{role.name}"]) for role in REGISTRY[relation].roles)))
    return GraphCandidate(tuple(relations), "accept")
