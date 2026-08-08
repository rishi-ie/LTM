"""Registry-constrained relation/role candidate construction for G2.6."""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import product

from topology_g1.registry import REGISTRY


@dataclass(frozen=True, slots=True)
class GoldenAtomInput:
    atom_id: str
    kind: str


@dataclass(frozen=True, slots=True)
class StructuredCandidate:
    relation_type: str | None
    role_bindings: tuple[tuple[str, tuple[str, ...]], ...]
    disposition: str


def enumerate_candidates(atoms: tuple[GoldenAtomInput, ...]) -> tuple[StructuredCandidate, ...]:
    """Enumerate only complete G1-legal assignments plus safe null actions."""
    candidates: list[StructuredCandidate] = [
        StructuredCandidate(None, (), "clarification_required"),
        StructuredCandidate(None, (), "quarantine"),
    ]
    for relation_name, specification in REGISTRY.items():
        slots = [
            role
            for role in specification.roles
            for _ in range(role.minimum)
        ]
        eligible = [
            [atom for atom in atoms if atom.kind in {kind.value for kind in role.allowed_kinds}]
            for role in slots
        ]
        if any(not values for values in eligible):
            continue
        for selected in product(*eligible):
            if len({item.atom_id for item in selected}) != len(selected):
                continue
            grouped: dict[str, list[str]] = {}
            for role, atom in zip(slots, selected, strict=True):
                grouped.setdefault(role.name, []).append(atom.atom_id)
            bindings = tuple((role.name, tuple(grouped[role.name])) for role in specification.roles)
            candidates.append(StructuredCandidate(relation_name, bindings, "accept"))
    return tuple(candidates)


def choose_candidate(
    candidates: tuple[StructuredCandidate, ...], scores: tuple[float, ...], *, probability_floor: float, margin_floor: float
) -> StructuredCandidate:
    """Commit only a calibrated, non-ambiguous complete candidate."""
    if len(candidates) != len(scores) or not candidates:
        raise ValueError("candidate scores are invalid")
    ordered = sorted(range(len(candidates)), key=lambda index: (-scores[index], index))
    first, second = ordered[0], ordered[1] if len(ordered) > 1 else ordered[0]
    largest = scores[first]
    probability = math.exp(largest - largest) / sum(math.exp(value - largest) for value in scores)
    if (
        candidates[first].disposition != "accept"
        or probability < probability_floor
        or scores[first] - scores[second] < margin_floor
    ):
        return StructuredCandidate(None, (), "clarification_required")
    return candidates[first]
