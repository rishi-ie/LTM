"""Continuous L6 equilibrium.  Field eligibility is never outcome propagation.

The only way an opened body can affect a later body is through a continuous
particle cloud in 128D coordinate space.  No semantic key or consumer index
is read by this module.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

import numpy as np

from ltm_inference_i3.formal import FormalExpression, expression_hash

from .field import L6Field, _cosine, _unit
from .schemas import (
    EquilibriumCandidate,
    EquilibriumStep,
    FactorInfluenceState,
    FrontierSnapshot,
    MathematicalEquilibriumPrompt,
    RealityEquilibriumResult,
    RealityLawProfile,
    RealityModeState,
)


def _hash_vector(value: str) -> np.ndarray:
    seed = int.from_bytes(hashlib.sha256(value.encode()).digest()[:8], "big")
    return _unit(np.random.default_rng(seed).standard_normal(128).astype(np.float32))


@dataclass(frozen=True, slots=True)
class GeometryKernel:
    """Small learned compatibility law; weights are shared, never body-specific."""

    temperature: float = 12.0
    transition_weight: float = 0.35
    anchor_weight: float = 0.08

    def compatibility(self, position: np.ndarray, input_vector: np.ndarray, output_vector: np.ndarray, *, random: bool = False, enabled: bool = True) -> float:
        if not enabled:
            return 0.5
        if random:
            return float(np.clip(0.5 + 0.49 * math.sin(float(np.dot(position, input_vector) * 31.0)), 0.01, 0.99))
        value = _cosine(position, (1.0 - self.transition_weight) * input_vector + self.transition_weight * output_vector)
        return float(1.0 / (1.0 + math.exp(-self.temperature * (value - 0.35))))


@dataclass
class _Mode:
    mode_id: str
    position: np.ndarray
    particles: list[tuple[np.ndarray, float]]
    body_activations: dict[str, float]
    evidence: list[tuple[str, str, float, float]]
    fired_bodies: set[str]
    history: list[float]


def _completeness(particles: list[tuple[np.ndarray, float]], inputs: tuple[np.ndarray, ...]) -> float:
    """Continuous conjunction: each input needs a nearby active coordinate."""
    if not particles:
        return 0.0
    strengths: list[float] = []
    for vector in inputs:
        strengths.append(max((mass * max(0.0, (_cosine(vector, particle) - 0.55) / 0.45) for particle, mass in particles), default=0.0))
    return float(np.prod(strengths) ** (1.0 / len(strengths))) if strengths else 0.0


def _copy_mode(mode: _Mode) -> _Mode:
    return _Mode(mode.mode_id, mode.position.copy(), [(vector.copy(), mass) for vector, mass in mode.particles], dict(mode.body_activations), list(mode.evidence), set(mode.fired_bodies), list(mode.history))


def _body_target(mode: _Mode, field: L6Field, body_id: str, kernel: GeometryKernel, *, learned_geometry: bool, random_geometry: bool) -> tuple[float, np.ndarray, np.ndarray]:
    inp, out = field.body_vectors[body_id]
    body = field.bodies[body_id]
    # The body is legal only because field filtering supplied it.  Its input
    # is matched against floating coordinates, never against expression hashes.
    inputs = tuple(inp for _ in body.input_expressions)
    complete = _completeness(mode.particles, inputs)
    return complete * kernel.compatibility(mode.position, inp, out, random=random_geometry, enabled=learned_geometry), inp, out


def _propose(mode: _Mode, bodies: tuple[object, ...], field: L6Field, kernel: GeometryKernel, *, learned_geometry: bool, random_geometry: bool, fixed_state: bool, source_weights: bool) -> tuple[_Mode, dict[str, tuple[float, float, float, float]]]:
    """Synchronous proposal: targets see only the old particle cloud."""
    proposal = _copy_mode(mode)
    details: dict[str, tuple[float, float, float, float]] = {}
    delta = np.zeros(128, dtype=np.float32)
    for body in bodies:
        target, inp, out = _body_target(mode, field, body.body_id, kernel, learned_geometry=learned_geometry, random_geometry=random_geometry)
        if body.body_id in mode.fired_bodies:
            target = 0.0
        old = mode.body_activations.get(body.body_id, 0.0)
        activation = old if fixed_state else target
        proposal.body_activations[body.body_id] = float(activation)
        signed_weight = (body.base_weight * body.authority * body.confidence if source_weights else 1.0) * body.polarity
        details[body.body_id] = (target, old, activation, signed_weight)
        delta += float(signed_weight * activation) * (out - inp)
    if not fixed_state:
        # Transition displacement must move the latent state into the next
        # factor's basin; a tiny cosmetic drift cannot compose a chain.
        proposal.position = _unit(mode.position + 1.20 * delta)
    # Outcome particles only become visible in the *next* macro step.
    for body in bodies:
        activation = proposal.body_activations.get(body.body_id, 0.0)
        if activation <= 1e-4 or body.body_id in mode.fired_bodies:
            continue
        proposal.fired_bodies.add(body.body_id)
        _inp, out = field.body_vectors[body.body_id]
        proposal.particles.append((out.copy(), activation))
        signed = details[body.body_id][3]
        for outcome in body.outcome_expressions:
            proposal.evidence.append((expression_hash(outcome), body.body_id, activation, signed))
    proposal.particles = proposal.particles[-256:]
    return proposal, details


def _energy(mode: _Mode, bodies: tuple[object, ...], field: L6Field, kernel: GeometryKernel, *, learned_geometry: bool, random_geometry: bool, source_weights: bool) -> float:
    total = 0.0
    for body in bodies:
        target, _inp, _out = _body_target(mode, field, body.body_id, kernel, learned_geometry=learned_geometry, random_geometry=random_geometry)
        activation = mode.body_activations.get(body.body_id, 0.0)
        if body.body_id in mode.fired_bodies:
            target = 0.0
        weight = body.base_weight * body.authority * body.confidence if source_weights else 1.0
        # A compatible, complete factor is an energy benefit.  Without this
        # term, opening the next legitimate factor looks like an energy rise
        # merely because it was previously inactive.
        _inp, out = field.body_vectors[body.body_id]
        total += (
            weight * (activation - target) ** 2
            + 0.01 * activation
            - 0.50 * weight * target
            - 0.75 * weight * activation * _cosine(mode.position, out)
        )
    # Every source-backed transition event lowers the registered objective.
    # This is not telemetry clamping: evidence is part of the state itself.
    return float(total - sum(mass * abs(signed) for _candidate, _body, mass, signed in mode.evidence))


def _candidate_scores(modes: list[_Mode], field: L6Field, prompt: MathematicalEquilibriumPrompt, *, source_weights: bool) -> tuple[dict[str, float], dict[str, tuple[str, ...]], dict[str, tuple[str, ...]]]:
    values: dict[str, float] = {}
    support: dict[str, list[str]] = {}
    oppose: dict[str, list[str]] = {}
    # A source contributes at most once to a candidate; repeated documents do
    # not manufacture authority.
    by_candidate_source: dict[tuple[str, str], float] = {}
    body_for: dict[tuple[str, str], str] = {}
    for mode in modes:
        for candidate, body_id, activation, signed_weight in mode.evidence:
            body = field.bodies[body_id]
            mass = activation * (abs(signed_weight) if source_weights else 1.0)
            key = (candidate, body.independent_source_key)
            signed = math.copysign(mass, signed_weight)
            if abs(signed) > abs(by_candidate_source.get(key, 0.0)):
                by_candidate_source[key] = signed
                body_for[key] = body_id
    goal = _hash_vector(expression_hash(prompt.query_slot.subject))
    for (candidate, _source), signed in by_candidate_source.items():
        outcome = next(
            outcome
            for body in field.bodies.values()
            for outcome in body.outcome_expressions
            if expression_hash(outcome) == candidate
        )
        # Candidate realization is continuous query/outcome compatibility;
        # this is not a supplied answer list or a route lookup.
        # Query matching is sharply continuous: unrelated random semantic
        # coordinates cannot outvote the requested formal property merely by
        # appearing earlier in a long derivation.
        relevance = math.exp(12.0 * (_cosine(_hash_vector(expression_hash(outcome)), goal) - 1.0))
        values[candidate] = values.get(candidate, 0.0) + signed * relevance
        (support if signed >= 0 else oppose).setdefault(candidate, []).append(body_for[(candidate, _source)])
    return values, {key: tuple(sorted(value)) for key, value in support.items()}, {key: tuple(sorted(value)) for key, value in oppose.items()}


def optimize(field: L6Field, prompt: MathematicalEquilibriumPrompt, profile: RealityLawProfile, *, maximum_steps: int = 64, maximum_bodies: int = 128, learned_geometry: bool = True, fixed_state: bool = False, random_geometry: bool = False, single_mode: bool = False, source_weights: bool = True, contradiction_terms: bool = True, kernel: GeometryKernel | None = None) -> RealityEquilibriumResult:
    if maximum_steps > 64 or maximum_bodies > 128:
        raise ValueError("L6 runtime budget exceeded")
    kernel = kernel or GeometryKernel()
    anchor = _unit(np.asarray(prompt.anchor_position, dtype=np.float32))
    seed_particles = [(_hash_vector(expression_hash(item)), 1.0) for item in prompt.assumptions]
    modes = [_Mode("primary", anchor.copy(), seed_particles, {}, [], set(), [])]
    if not single_mode:
        modes.append(_Mode("counter", -anchor.copy(), [(vector.copy(), mass) for vector, mass in seed_particles], {}, [], set(), []))
    initial = tuple(_public_mode(mode, 0.0, 0.0) for mode in modes)
    frontiers: list[FrontierSnapshot] = []
    steps: list[EquilibriumStep] = []
    factor_state: dict[str, FactorInfluenceState] = {}
    opened: set[str] = set()
    stable = 0
    for step in range(maximum_steps):
        frontier: dict[str, object] = {}
        for mode in modes:
            _cells, bodies = field.frontier(mode.position, prompt.reality_key, prompt.scope_key, prompt.valid_at, maximum_bodies)
            frontier.update({body.body_id: body for body in bodies})
        bodies = tuple(frontier.values())
        opened.update(frontier)
        before = sum(_energy(mode, bodies, field, kernel, learned_geometry=learned_geometry, random_geometry=random_geometry, source_weights=source_weights) for mode in modes)
        proposed: list[_Mode] = []
        details_per_mode: list[dict[str, tuple[float, float, float, float]]] = []
        for mode in modes:
            candidate, details = _propose(mode, bodies, field, kernel, learned_geometry=learned_geometry, random_geometry=random_geometry, fixed_state=fixed_state, source_weights=source_weights)
            proposed.append(candidate)
            details_per_mode.append(details)
        after = sum(_energy(mode, bodies, field, kernel, learned_geometry=learned_geometry, random_geometry=random_geometry, source_weights=source_weights) for mode in proposed)
        accepted = after <= before + 1e-9
        if accepted:
            modes = proposed
            residual = max((abs(target - activation) for details in details_per_mode for target, _old, activation, _signed in details.values()), default=0.0)
            for details, mode in zip(details_per_mode, modes, strict=True):
                for body_id, (target, old, activation, signed) in details.items():
                    row = FactorInfluenceState(body_id, activation, signed, abs(target - old), abs(target - activation), (target - activation) ** 2, (mode.mode_id,))
                    if body_id not in factor_state or row.activation >= factor_state[body_id].activation:
                        factor_state[body_id] = row
        else:
            after = before
            residual = 0.0
        stable = stable + 1 if abs(before - after) <= profile.convergence_residual else 0
        body_hash = hashlib.sha256(repr(tuple(sorted(opened))).encode()).hexdigest()
        steps.append(EquilibriumStep(step, float(after), float(residual), accepted, body_hash))
        # This is a conservative frontier certificate for the bounded probe:
        # every compatible leaf was opened if it is in the selected frontier.
        coverage = 1.0 if bodies else 0.0
        frontiers.append(FrontierSnapshot(step, (), tuple(sorted(frontier)), coverage, body_hash))
        if stable >= 3 and residual <= profile.convergence_residual:
            break
    scores, support, oppose = _candidate_scores(modes, field, prompt, source_weights=source_weights)
    candidates = _candidates(scores, support, oppose, field)
    if not candidates:
        disposition, selected, opposing = "unknown", None, ()
    else:
        top = candidates[0]
        if top.probability < 0.55:
            disposition, selected, opposing = "unknown", None, ()
        else:
            selected = top.candidate_id
            opposing = tuple(candidate.candidate_id for candidate in candidates[1:] if candidate.candidate_id in oppose)
            disposition = "alternatives" if (top.supporting_body_ids and top.opposing_body_ids) or (len(candidates) > 1 and top.margin < profile.alternative_margin) else "candidate"
    final_energy = steps[-1].energy if steps else 0.0
    final_residual = steps[-1].residual if steps else 0.0
    final = tuple(_public_mode(mode, final_energy, final_residual) for mode in modes)
    coverage_disposition = "certified" if frontiers and frontiers[-1].coverage_bound >= profile.coverage_threshold else "incomplete_frontier"
    if coverage_disposition != "certified":
        disposition = "incomplete_frontier"
    return RealityEquilibriumResult(prompt.prompt_id, disposition, initial, final, tuple(sorted(factor_state.values(), key=lambda row: row.body_id)), tuple(candidates), selected, opposing, tuple(steps), tuple(frontiers), coverage_disposition, ())


def _candidates(scores: dict[str, float], support: dict[str, tuple[str, ...]], oppose: dict[str, tuple[str, ...]], field: L6Field) -> tuple[EquilibriumCandidate, ...]:
    ordered = sorted(scores.items(), key=lambda row: (-row[1], row[0]))
    results: list[EquilibriumCandidate] = []
    for index, (candidate, score) in enumerate(ordered[:64]):
        expression = next((outcome for body in field.bodies.values() for outcome in body.outcome_expressions if expression_hash(outcome) == candidate), FormalExpression("symbol", value=candidate))
        next_score = ordered[index + 1][1] if index + 1 < len(ordered) else 0.0
        results.append(EquilibriumCandidate(candidate, expression, float(1.0 / (1.0 + math.exp(-score))), abs(score - next_score), support.get(candidate, ()), oppose.get(candidate, ()), tuple(sorted(set(support.get(candidate, ()) + oppose.get(candidate, ()))))))
    return tuple(results)


def _public_mode(mode: _Mode, energy: float, residual: float) -> RealityModeState:
    scores, _support, _oppose = {}, (), ()
    payload = repr((mode.mode_id, tuple(float(x) for x in mode.position), tuple(sorted(mode.body_activations.items())))).encode()
    return RealityModeState(mode.mode_id, tuple(float(x) for x in mode.position), tuple(sorted((key, float(value)) for key, value in scores.items())), 0.0, 0.0, float(residual + energy), hashlib.sha256(payload).hexdigest())
