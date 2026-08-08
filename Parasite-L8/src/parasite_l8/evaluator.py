"""Independent numerical verifier; this module intentionally does not import optimizer."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from .contracts import CompiledPolicy, L8Result
from .policy import policy_values


def _solve_reference(atoms: tuple[Any, ...], factors: tuple[Any, ...], assumptions: tuple[str, ...], query_expression: str, query_sort: str, policy: CompiledPolicy, source_classes: dict[str, str], scope: str, valid_at: int | None) -> tuple[str, str | None, dict[str, float], dict[str, float]]:
    source_classes = dict(source_classes or {})
    values = policy_values(policy, scope, source_classes)
    ids = {atom.atom_id for atom in atoms}
    if not set(assumptions) <= ids:
        raise ValueError("ASSUMPTION_ATOM_MISSING")
    active = [item for item in factors if item.scope_key in {"global", scope} and not (valid_at is not None and ((item.valid_from is not None and item.valid_from > valid_at) or (item.valid_to is not None and item.valid_to < valid_at)))]
    if values.get("require_source_class"):
        active = [item for item in active if source_classes.get(item.independent_source_key, item.independent_source_key) == values["require_source_class"]]
    pos = {atom: 1.0 if atom in assumptions else 0.0 for atom in ids}
    neg = dict.fromkeys(ids, 0.0)
    for _ in range(256):
        targets = {}
        for item in active:
            inputs = [pos[key] for key in item.input_atom_ids]
            targets[item.body_id] = min(inputs) if values["conjunction_mode"] == "all" else sorted(inputs, reverse=True)[min(len(inputs), int(values["conjunction_mode"]["k"])) - 1]
        grouped = defaultdict(list)
        for item in active:
            cls = source_classes.get(item.independent_source_key, item.independent_source_key)
            mult = float(values["source_multiplier"].get(cls, values["source_multiplier"].get(item.independent_source_key, 1.0)))
            grouped[(item.outcome_atom_id, item.outcome_polarity, item.independent_source_key)].append((item.weight * mult * targets[item.body_id], item.body_id))
        channels = defaultdict(list)
        for (atom, polarity, source), rows in grouped.items():
            channels[(atom, polarity)].append(max(rows))
        new_pos, new_neg = {}, {}
        for atom in ids:
            new_pos[atom] = 1.0 if atom in assumptions else 1.0 - math.prod(1 - max(0.0, min(1.0, value)) for value, _ in channels[(atom, 1)])
            new_neg[atom] = 1.0 - math.prod(1 - max(0.0, min(1.0, value)) for value, _ in channels[(atom, -1)])
        delta = max(max((abs(new_pos[k] - pos[k]) for k in ids), default=0.0), max((abs(new_neg[k] - neg[k]) for k in ids), default=0.0))
        pos, neg = new_pos, new_neg
        if delta <= 1e-8:
            break
    candidates = []
    for atom in atoms:
        if atom.expression != query_expression or atom.sort != query_sort:
            continue
        for polarity, activation, opposing in ((1, pos[atom.atom_id], neg[atom.atom_id]), (-1, neg[atom.atom_id], pos[atom.atom_id])):
            if activation >= float(values["candidate_threshold"]):
                candidates.append((atom.atom_id, polarity, activation, opposing))
    candidates.sort(key=lambda row: (-row[2], row[0], row[1]))
    expected = "unknown" if not candidates else ("alternatives" if len(candidates) > 1 and abs(candidates[0][2] - candidates[1][2]) <= float(values["conflict_margin"]) else "candidate")
    selected = None if expected != "candidate" else f"{candidates[0][0]}:{candidates[0][1]:+d}"
    return expected, selected, pos, neg


def expected_outcome(atoms: tuple[Any, ...], factors: tuple[Any, ...], assumptions: tuple[str, ...], query_expression: str, query_sort: str, policy: CompiledPolicy, source_classes: dict[str, str] | None = None, scope: str = "global", valid_at: int | None = None) -> dict[str, Any]:
    disposition, selected, positive, negative = _solve_reference(atoms, factors, assumptions, query_expression, query_sort, policy, dict(source_classes or {}), scope, valid_at)
    return {"disposition": disposition, "selected_candidate_id": selected, "positive": positive, "negative": negative}


def verify_result(result: L8Result, atoms: tuple[Any, ...], factors: tuple[Any, ...], assumptions: tuple[str, ...], query_expression: str, query_sort: str, policy: CompiledPolicy, source_classes: dict[str, str] | None = None, scope: str = "global", valid_at: int | None = None) -> dict[str, Any]:
    """Replay state equations independently and compare public result fields."""
    expected = expected_outcome(atoms, factors, assumptions, query_expression, query_sort, policy, source_classes, scope, valid_at)
    state_ok = all(abs(dict(result.positive).get(key, -1) - value) <= 1e-7 for key, value in expected["positive"].items())
    return {"verified": state_ok and result.disposition == expected["disposition"] and result.selected_candidate_id == expected["selected_candidate_id"], "expected_disposition": expected["disposition"], "state_match": state_ok, "candidate_count": len(result.candidates)}
