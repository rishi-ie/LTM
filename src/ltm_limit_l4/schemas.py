"""Immutable public contracts for L4."""

from __future__ import annotations

from dataclasses import dataclass

from ltm_inference_i3.schemas import FormalExpression


@dataclass(frozen=True, slots=True)
class L4Problem:
    problem_id: str
    source: FormalExpression
    goal: FormalExpression
    reality_key: str
    maximum_steps: int = 64
    maximum_bodies_per_state: int = 64
    maximum_legal_proposals: int = 128
    beam_width: int = 16

    def __post_init__(self) -> None:
        if not self.problem_id or self.reality_key != "standard-l4-v1":
            raise ValueError("invalid L4 problem identity")
        if not 1 <= self.maximum_steps <= 64:
            raise ValueError("invalid proof-step budget")
        if not 1 <= self.maximum_bodies_per_state <= 64:
            raise ValueError("invalid body budget")
        if not 1 <= self.maximum_legal_proposals <= 128:
            raise ValueError("invalid proposal budget")
        if not 1 <= self.beam_width <= 16:
            raise ValueError("invalid beam width")


@dataclass(frozen=True, slots=True)
class ExactAxiomApplication:
    body_id: str
    axiom_id: str
    site_path: tuple[int, ...]
    reverse: bool
    substitution_hash: str
    before_hash: str
    after_hash: str


@dataclass(frozen=True, slots=True)
class L4ProofStep:
    application: ExactAxiomApplication
    before: FormalExpression
    after: FormalExpression


@dataclass(frozen=True, slots=True)
class L4SearchTrace:
    step: int
    state_hash: str
    legal_proposal_count: int
    retained_proposals: tuple[ExactAxiomApplication, ...]
    beam_state_hashes: tuple[str, ...]
    bodies_opened: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class L4InferenceResult:
    problem_id: str
    disposition: str
    proof: tuple[L4ProofStep, ...]
    states_explored: int
    bodies_opened: tuple[str, ...]
    traces: tuple[L4SearchTrace, ...]
    failure_codes: tuple[str, ...]
    factual_operations: tuple[()] = ()

    def __post_init__(self) -> None:
        if self.factual_operations:
            raise ValueError("L4 cannot mutate factual topology")
        if self.disposition not in {"proved", "refuted", "unknown", "quarantine"}:
            raise ValueError("invalid L4 disposition")


@dataclass(frozen=True, slots=True)
class ExecutableAxiomRecord:
    axiom_id: str
    family: str
    forward: bool
    reverse: bool
    body_id: str
    schema_hash: str


@dataclass(frozen=True, slots=True)
class Proposal:
    axiom_id: str
    body_id: str
    path: tuple[int, ...]
    reverse: bool
    after: FormalExpression
    substitution_hash: str


@dataclass(frozen=True, slots=True)
class GoldRecord:
    problem_id: str
    status: str
    depth: int
    proof: tuple[L4ProofStep, ...]
    family: str
    branching: int
    paired: bool
    detour: bool
    shortest_certified: bool


FORBIDDEN_PUBLIC_FIELDS = frozenset(
    {
        "expected_depth",
        "required_axiom_ids",
        "required_body_ids",
        "proof_certificate",
        "answer_candidates",
        "route_identifier",
        "template_identifier",
        "evaluator_path",
        "depth",
        "proof",
    }
)
