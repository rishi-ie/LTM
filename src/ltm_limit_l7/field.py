"""Fixed L7 factor graph.  It deliberately has no consumer-propagation API."""

from __future__ import annotations

from dataclasses import dataclass

from .schemas import Atom, RealityFactor


@dataclass(frozen=True, slots=True)
class RealityField:
    atoms: tuple[Atom, ...]
    factors: tuple[RealityFactor, ...]

    def __post_init__(self) -> None:
        ids = {atom.atom_id for atom in self.atoms}
        if len(ids) != len(self.atoms) or any(set(factor.input_atom_ids + (factor.outcome_atom_id,)) - ids for factor in self.factors):
            raise ValueError("invalid L7 field references")

    def applicable(self, reality_key: str, scope_key: str, valid_at: int | None, *, ignore_reality: bool = False) -> tuple[RealityFactor, ...]:
        rows = []
        for factor in self.factors:
            if not ignore_reality and factor.reality_key != reality_key:
                continue
            if factor.scope_key not in {"global", scope_key}:
                continue
            if valid_at is not None and ((factor.valid_from is not None and factor.valid_from > valid_at) or (factor.valid_to is not None and factor.valid_to < valid_at)):
                continue
            rows.append(factor)
        return tuple(rows)
