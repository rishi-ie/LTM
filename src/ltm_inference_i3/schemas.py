"""Immutable public contracts for I3.

The runtime receives formal expressions and registered axiom bodies, never an
answer, gold trace, required-body set, or proof depth.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FormalExpression:
    op: str
    args: tuple[FormalExpression, ...] = ()
    value: str | None = None

    def __post_init__(self) -> None:
        if not self.op:
            raise ValueError("expression operator is required")
        if self.op in {"var", "int"} and self.value is None:
            raise ValueError("leaf expression requires a value")


@dataclass(frozen=True, slots=True)
class FormalProposition:
    relation: str
    left: FormalExpression
    right: FormalExpression


@dataclass(frozen=True, slots=True)
class AxiomSchema:
    axiom_id: str
    family: str
    left: FormalExpression
    right: FormalExpression
    reversible: bool
    reality_key: str


@dataclass(frozen=True, slots=True)
class MathRealityManifest:
    reality_key: str
    revision: str
    axiom_ids: tuple[str, ...]
    profile_hash: str


@dataclass(frozen=True, slots=True)
class MathematicalBody:
    body_id: str
    axiom_id: str
    reality_key: str
    vector_ref: int
    body_hash: str


@dataclass(frozen=True, slots=True)
class TheoremProblem:
    problem_id: str
    assumptions: tuple[FormalProposition, ...]
    goal: FormalProposition
    reality_key: str
    maximum_bodies: int
    maximum_steps: int

    def __post_init__(self) -> None:
        if not 1 <= self.maximum_bodies <= 64 or not 1 <= self.maximum_steps <= 64:
            raise ValueError("invalid I3 proof budget")


@dataclass(frozen=True, slots=True)
class ProofState:
    current: FormalExpression
    goal: FormalExpression
    used_axiom_ids: tuple[str, ...]
    state_hash: str


@dataclass(frozen=True, slots=True)
class AxiomProposal:
    axiom_id: str
    path: tuple[int, ...]
    reverse: bool
    score: float
    energy: float


@dataclass(frozen=True, slots=True)
class FormalProofStep:
    axiom_id: str
    path: tuple[int, ...]
    reverse: bool
    before: FormalExpression
    after: FormalExpression


@dataclass(frozen=True, slots=True)
class VerifiedProof:
    conclusion: FormalProposition
    steps: tuple[FormalProofStep, ...]
    status: str
    proof_hash: str


@dataclass(frozen=True, slots=True)
class MathematicalInferenceResult:
    problem_id: str
    disposition: str
    proof: tuple[FormalProofStep, ...]
    opened_body_ids: tuple[str, ...]
    states_visited: int
    energy_trace: tuple[float, ...]
    failure_codes: tuple[str, ...]
    factual_operations: tuple[()] = ()

    def __post_init__(self) -> None:
        if self.factual_operations:
            raise ValueError("I3 emits no factual operations")
