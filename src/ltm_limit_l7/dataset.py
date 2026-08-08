"""Small, deterministic shared mathematical reality for L7."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace

from .field import RealityField
from .schemas import Atom, PublicPrompt, RealityFactor


@dataclass(frozen=True, slots=True)
class ExpectedOutcome:
    disposition: str
    selected_atom_id: str | None
    depth: int | None
    family: str


@dataclass(frozen=True, slots=True)
class L7Case:
    public: PublicPrompt
    expected: ExpectedOutcome


def _atom(prefix: str, level: int, reality: str = "standard", *, scope: str = "global") -> Atom:
    # Canonical, typed formal expression notation.  The exact body law only
    # consumes atom identities; the expression is for query/realization.
    expression = f"Eq(add^{level}({prefix},0),{prefix})"
    return Atom(f"{reality}:{scope}:{prefix}:{level}", expression, "proposition", reality, scope)


def _factor(body_id: str, inputs: tuple[str, ...], outcome: str, reality: str, source: str, *, polarity: int = 1, weight: float = 1.0, scope: str = "global") -> RealityFactor:
    return RealityFactor(body_id, reality, inputs, outcome, polarity, weight, 1.0, 1.0, source, scope, provenance_ids=(body_id,))


def build_reality() -> RealityField:
    atoms: list[Atom] = []
    factors: list[RealityFactor] = []
    lanes: list[tuple[str, str]] = []
    # 160 standard and 80 custom transformation bodies.  Every body is a
    # registered add-zero-style equality transformation in canonical form.
    for reality, count in (("standard", 4), ("custom:alpha", 2), ("custom:beta", 2)):
        for lane in range(count):
            prefix = f"{reality.replace(':', '_')}_lane_{lane}"
            rows = tuple(_atom(prefix, level, reality) for level in range(21))
            atoms.extend(rows)
            lanes.append((reality, prefix))
            for level in range(20):
                factors.append(_factor(f"chain:{reality}:{lane}:{level}", (rows[level].atom_id,), rows[level + 1].atom_id, reality, f"source:{reality}:{lane}:{level}"))
    # 12 independently sourced contradiction fixtures, half weighted and
    # half balanced.  Each is source-backed and isolated from ordinary lanes.
    for index in range(12):
        reality, prefix = "standard", f"conflict_{index}"
        rows = tuple(_atom(prefix, level, reality) for level in range(5))
        atoms.extend(rows)
        for level in range(4):
            factors.append(_factor(f"conflict:path:{index}:{level}", (rows[level].atom_id,), rows[level + 1].atom_id, reality, f"source:conflict:{index}:{level}"))
        weight = 0.35 if index < 6 else 1.0
        factors.append(_factor(f"conflict:negative:{index}", (rows[3].atom_id,), rows[4].atom_id, reality, f"source:conflict:negative:{index}", polarity=-1, weight=weight))
    # Twelve conjunction fixtures: no outcome can activate until both source
    # atoms are clamped by the prompt.
    for index in range(12):
        left, right, outcome = _atom(f"and_left_{index}", 0), _atom(f"and_right_{index}", 0), _atom(f"and_outcome_{index}", 1)
        atoms.extend((left, right, outcome))
        factors.append(_factor(f"and:{index}", (left.atom_id, right.atom_id), outcome.atom_id, "standard", f"source:and:{index}"))
    # Scope/time fixtures are genuine masked constraints, not merely unknown
    # query strings.  The body is legal only for a private prompt at time 7.
    for index in range(8):
        start = _atom(f"scoped_start_{index}", 0, scope="private")
        outcome = _atom(f"scoped_outcome_{index}", 1, scope="private")
        atoms.extend((start, outcome))
        factor = _factor(f"scoped:{index}", (start.atom_id,), outcome.atom_id, "standard", f"source:scoped:{index}", scope="private")
        factors.append(replace(factor, valid_from=5, valid_to=10))
    # 80 valid but irrelevant branches; their inputs are active on some
    # chains, but their outcomes never match a prompt goal.
    for index in range(80):
        reality, prefix = lanes[index % len(lanes)]
        source = next(atom for atom in atoms if atom.atom_id == f"{reality}:global:{prefix}:{index % 20}")
        decoy = _atom(f"decoy_{index}", 0, reality)
        atoms.append(decoy)
        factors.append(_factor(f"branch:{index}", (source.atom_id,), decoy.atom_id, reality, f"source:branch:{index}"))
    # Fill to the fixed 512-body commitment with legal disconnected facts.
    while len(factors) < 512:
        index = len(factors)
        left, right = _atom(f"distractor_{index}", 0), _atom(f"distractor_{index}", 1)
        atoms.extend((left, right))
        factors.append(_factor(f"distractor:{index}", (left.atom_id,), right.atom_id, "standard", f"source:distractor:{index}"))
    if len(factors) != 512:
        raise AssertionError("L7 field must contain exactly 512 bodies")
    return RealityField(tuple(atoms), tuple(factors))


def _lane_atom(field: RealityField, reality: str, prefix: str, level: int, *, scope: str = "global") -> Atom:
    return next(atom for atom in field.atoms if atom.atom_id == f"{reality}:{scope}:{prefix}:{level}")


def build_cases(field: RealityField) -> tuple[L7Case, ...]:
    cases: list[L7Case] = []
    lanes = (("standard", "standard_lane_0"), ("standard", "standard_lane_1"), ("standard", "standard_lane_2"), ("standard", "standard_lane_3"), ("custom:alpha", "custom_alpha_lane_0"), ("custom:alpha", "custom_alpha_lane_1"), ("custom:beta", "custom_beta_lane_0"), ("custom:beta", "custom_beta_lane_1"))
    for depth in range(1, 21):
        for lane_index, (reality, prefix) in enumerate(lanes):
            start, goal = _lane_atom(field, reality, prefix, 0), _lane_atom(field, reality, prefix, depth)
            prompt = PublicPrompt(f"unique:{depth}:{lane_index}", (start.atom_id,), goal.expression, "proposition", reality)
            cases.append(L7Case(prompt, ExpectedOutcome("candidate", goal.atom_id, depth, "unique")))
    for index in range(6):
        goal = _lane_atom(field, "standard", f"conflict_{index}", 4)
        start = _lane_atom(field, "standard", f"conflict_{index}", 0)
        for repeat in range(4):
            cases.append(L7Case(PublicPrompt(f"weighted:{index}:{repeat}", (start.atom_id,), goal.expression, "proposition", "standard"), ExpectedOutcome("candidate", goal.atom_id, 4, "weighted_contradiction")))
    for index in range(6, 12):
        goal = _lane_atom(field, "standard", f"conflict_{index}", 4)
        start = _lane_atom(field, "standard", f"conflict_{index}", 0)
        for repeat in range(2):
            cases.append(L7Case(PublicPrompt(f"balanced:{index}:{repeat}", (start.atom_id,), goal.expression, "proposition", "standard"), ExpectedOutcome("alternatives", goal.atom_id, 4, "balanced_alternative")))
    for index in range(12):
        left = _lane_atom(field, "standard", f"and_left_{index}", 0)
        right = _lane_atom(field, "standard", f"and_right_{index}", 0)
        goal = _lane_atom(field, "standard", f"and_outcome_{index}", 1)
        assumptions = (left.atom_id, right.atom_id) if index < 6 else (left.atom_id,)
        expected = ExpectedOutcome("candidate", goal.atom_id, 1, "conjunction") if index < 6 else ExpectedOutcome("unknown", None, None, "conjunction")
        cases.append(L7Case(PublicPrompt(f"and:{index}", assumptions, goal.expression, "proposition", "standard"), expected))
    for index in range(12):
        start = _lane_atom(field, "standard", "standard_lane_0", 0)
        cases.append(L7Case(PublicPrompt(f"unknown:{index}", (start.atom_id,), f"Eq(unknown_{index},0)", "proposition", "standard"), ExpectedOutcome("unknown", None, None, "unknown")))
    for index in range(6):
        for reality in ("custom:alpha", "custom:beta"):
            prefix = f"{reality.replace(':', '_')}_lane_{index % 2}"
            start, goal = _lane_atom(field, reality, prefix, 0), _lane_atom(field, reality, prefix, 3)
            cases.append(L7Case(PublicPrompt(f"twin:{reality}:{index}", (start.atom_id,), goal.expression, "proposition", reality), ExpectedOutcome("candidate", goal.atom_id, 3, "counterfactual")))
    for index in range(8):
        start = _lane_atom(field, "standard", f"scoped_start_{index}", 0, scope="private")
        goal = _lane_atom(field, "standard", f"scoped_outcome_{index}", 1, scope="private")
        cases.append(L7Case(PublicPrompt(f"scope:{index}", (start.atom_id,), goal.expression, "proposition", "standard", scope_key="private", valid_at=7), ExpectedOutcome("candidate", goal.atom_id, 1, "scope_time")))
    if len(cases) != 240:
        raise AssertionError(f"expected 240 L7 cases, found {len(cases)}")
    return tuple(cases)


def manifest(field: RealityField, cases: tuple[L7Case, ...]) -> dict[str, object]:
    payload = repr((tuple(atom.atom_id for atom in field.atoms), tuple(factor.body_id for factor in field.factors), tuple(case.public.prompt_id for case in cases))).encode()
    return {"bodies": len(field.factors), "atoms": len(field.atoms), "prompts": len(cases), "sha256": hashlib.sha256(payload).hexdigest(), "trainable_parameters": 0}
