"""Immutable L6 contracts. Exact facts and continuous evidence are separate."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Any

from ltm_inference_i3.formal import FormalExpression, expression_hash


def _finite(value: float, name: str) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


@dataclass(frozen=True, slots=True)
class RealityLawProfile:
    reality_key: str
    revision: str
    executable_schema_manifest_hash: str
    contradiction_policy: str = "paraconsistent_weighted"
    source_mass_cap: float = 8.0
    alternative_margin: float = 0.05
    coverage_threshold: float = 0.99
    convergence_residual: float = 1e-3
    profile_hash: str = ""

    def __post_init__(self) -> None:
        if not self.reality_key or self.contradiction_policy != "paraconsistent_weighted":
            raise ValueError("invalid L6 reality law")
        if self.source_mass_cap <= 0 or not 0 < self.alternative_margin < 1:
            raise ValueError("invalid L6 profile bounds")
        if not self.profile_hash:
            payload = repr((self.reality_key, self.revision, self.executable_schema_manifest_hash, self.contradiction_policy, self.source_mass_cap, self.alternative_margin)).encode()
            object.__setattr__(self, "profile_hash", hashlib.sha256(payload).hexdigest())


@dataclass(frozen=True, slots=True)
class MathematicalRealityBody:
    body_id: str
    reality_key: str
    input_expressions: tuple[FormalExpression, ...]
    outcome_expressions: tuple[FormalExpression, ...]
    transition_vector_ref: int
    base_weight: float
    authority: float
    confidence: float
    polarity: int
    scope_key: str
    valid_from: int | None
    valid_to: int | None
    independent_source_key: str
    provenance_ids: tuple[str, ...]
    body_hash: str

    def __post_init__(self) -> None:
        if not self.body_id or not self.reality_key or not self.input_expressions or not self.outcome_expressions:
            raise ValueError("invalid mathematical body")
        if self.transition_vector_ref < 0 or self.polarity not in {-1, 1} or len(self.body_hash) != 64:
            raise ValueError("invalid mathematical body identity")
        for value, name in ((self.base_weight, "base_weight"), (self.authority, "authority"), (self.confidence, "confidence")):
            _finite(value, name)
            if not 0 <= value <= 1:
                raise ValueError(f"{name} outside [0,1]")
        if self.valid_from is not None and self.valid_to is not None and self.valid_from > self.valid_to:
            raise ValueError("invalid validity interval")

    @staticmethod
    def make(body_id: str, reality_key: str, inputs: tuple[FormalExpression, ...], outcomes: tuple[FormalExpression, ...], vector_ref: int, weight: float = 1.0, authority: float = 1.0, confidence: float = 1.0, polarity: int = 1, scope_key: str = "global", source: str = "source", provenance: tuple[str, ...] = ()) -> MathematicalRealityBody:
        raw = repr((body_id, reality_key, tuple(expression_hash(x) for x in inputs), tuple(expression_hash(x) for x in outcomes), vector_ref, weight, authority, confidence, polarity, scope_key, source, provenance)).encode()
        return MathematicalRealityBody(body_id, reality_key, inputs, outcomes, vector_ref, weight, authority, confidence, polarity, scope_key, None, None, source, provenance or (body_id,), hashlib.sha256(raw).hexdigest())


@dataclass(frozen=True, slots=True)
class MathematicalQuerySlot:
    subject: FormalExpression
    expected_sort: str
    requested_property: str


@dataclass(frozen=True, slots=True)
class MathematicalEquilibriumPrompt:
    prompt_id: str
    assumptions: tuple[FormalExpression, ...]
    query_slot: MathematicalQuerySlot
    reality_key: str
    scope_key: str
    valid_at: int | None
    anchor_position: tuple[float, ...]
    compiler_confidence: float = 1.0

    def __post_init__(self) -> None:
        if len(self.anchor_position) != 128 or any(not math.isfinite(x) for x in self.anchor_position):
            raise ValueError("anchor must be a finite 128D vector")
        if not 0 <= self.compiler_confidence <= 1:
            raise ValueError("invalid compiler confidence")


@dataclass(frozen=True, slots=True)
class FactorInfluenceState:
    body_id: str
    activation: float
    signed_weight: float
    residual_before: float
    residual_after: float
    energy_contribution: float
    affected_mode_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for x, name in ((self.activation, "activation"), (self.signed_weight, "signed_weight"), (self.residual_before, "residual_before"), (self.residual_after, "residual_after"), (self.energy_contribution, "energy_contribution")):
            _finite(x, name)
        if not 0 <= self.activation <= 1:
            raise ValueError("activation outside [0,1]")


@dataclass(frozen=True, slots=True)
class RealityModeState:
    mode_id: str
    semantic_position: tuple[float, ...]
    candidate_activations: tuple[tuple[str, float], ...]
    supporting_mass: float
    opposing_mass: float
    unresolved_residual: float
    state_hash: str

    def __post_init__(self) -> None:
        if len(self.semantic_position) != 128 or any(not math.isfinite(x) for x in self.semantic_position):
            raise ValueError("invalid mode state")
        for _, value in self.candidate_activations:
            if not 0 <= value <= 1 or not math.isfinite(value):
                raise ValueError("invalid candidate activation")


@dataclass(frozen=True, slots=True)
class EquilibriumCandidate:
    candidate_id: str
    expression: FormalExpression
    probability: float
    margin: float
    supporting_body_ids: tuple[str, ...]
    opposing_body_ids: tuple[str, ...]
    provenance_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EquilibriumStep:
    step: int
    energy: float
    residual: float
    accepted: bool
    frontier_hash: str


@dataclass(frozen=True, slots=True)
class FrontierSnapshot:
    step: int
    cell_ids: tuple[str, ...]
    body_ids: tuple[str, ...]
    coverage_bound: float
    frontier_hash: str


@dataclass(frozen=True, slots=True)
class RealityEquilibriumResult:
    prompt_id: str
    disposition: str
    initial_modes: tuple[RealityModeState, ...]
    final_modes: tuple[RealityModeState, ...]
    factor_states: tuple[FactorInfluenceState, ...]
    candidates: tuple[EquilibriumCandidate, ...]
    selected_candidate_id: str | None
    opposing_candidate_ids: tuple[str, ...]
    trajectory: tuple[EquilibriumStep, ...]
    frontiers: tuple[FrontierSnapshot, ...]
    coverage_disposition: str
    failure_codes: tuple[str, ...]
    factual_operations: tuple[()] = ()

    def __post_init__(self) -> None:
        if self.disposition not in {"candidate", "alternatives", "ambiguous", "unknown", "incomplete_frontier", "quarantine"}:
            raise ValueError("invalid L6 disposition")
        if self.factual_operations:
            raise ValueError("L6 cannot mutate factual topology")


@dataclass(frozen=True, slots=True)
class RealityEquilibriumCertificate:
    prompt_id: str
    candidate_id: str
    exact_derivation_paths: tuple[tuple[str, ...], ...]
    supporting_body_ids: tuple[str, ...]
    opposing_body_ids: tuple[str, ...]
    independent_source_keys: tuple[str, ...]
    unavoidably_unsatisfied_body_ids: tuple[str, ...]
    final_objective: float
    global_regret: float
    verified: bool
    certificate_hash: str


def public_prompt(prompt: MathematicalEquilibriumPrompt) -> dict[str, Any]:
    return {"prompt_id": prompt.prompt_id, "assumptions": [expression_hash(x) for x in prompt.assumptions], "query_sort": prompt.query_slot.expected_sort, "requested_property": prompt.query_slot.requested_property, "reality_key": prompt.reality_key, "scope_key": prompt.scope_key, "valid_at": prompt.valid_at, "anchor_position": list(prompt.anchor_position)}
