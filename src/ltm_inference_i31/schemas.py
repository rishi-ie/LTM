"""Immutable public and evaluator contracts for I3.1."""

from __future__ import annotations

from dataclasses import dataclass

from ltm_inference_i3.schemas import FormalExpression


@dataclass(frozen=True, slots=True)
class MathematicalBody:
    body_id: str
    reality_key: str
    left: FormalExpression
    right: FormalExpression
    provenance_hash: str
    vector_index: int


@dataclass(frozen=True, slots=True)
class TheoremProblem:
    problem_id: str
    reality_key: str
    source: FormalExpression
    goal: FormalExpression
    maximum_bodies: int
    maximum_steps: int


@dataclass(frozen=True, slots=True)
class FormalProofStep:
    body_id: str
    path: tuple[int, ...]
    reverse: bool
    before: FormalExpression
    after: FormalExpression


@dataclass(frozen=True, slots=True)
class MathematicalInferenceResult:
    problem_id: str
    disposition: str
    proof: tuple[FormalProofStep, ...]
    opened_body_ids: tuple[str, ...]
    state_count: int
    priorities: tuple[float, ...]
    failure_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SearchTraceEvent:
    step: int
    state_hash: str
    retrieval_mode: str
    frontier_body_ids: tuple[str, ...]
    legal_proposal_count: int
    retained: tuple[tuple[str, tuple[int, ...], bool, str, float], ...]
    state_count: int


@dataclass(frozen=True, slots=True)
class VerifiedMathEnvelope:
    envelope_id: str
    reality_key: str
    source_hash: str
    goal_hash: str
    proof_hash: str
    axiom_ids: tuple[str, ...]
    claim_entity: str
    claim_object: str
    provenance_hash: str


@dataclass(frozen=True, slots=True)
class PromptAuditRecord:
    prompt_text: str
    inference: MathematicalInferenceResult
    trace: tuple[SearchTraceEvent, ...]
    replay_valid: bool
    envelope: VerifiedMathEnvelope | None
    field_semantic_hash: str | None
    mumbrane_semantic_hash: str | None
    decoder_text: str | None
    controls: tuple[tuple[str, str, bool], ...]
