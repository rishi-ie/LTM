"""Frozen L2 contracts."""

from __future__ import annotations

from dataclasses import dataclass

from ltm_inference_i3.schemas import FormalExpression, TheoremProblem


@dataclass(frozen=True, slots=True)
class MathLanguageSource:
    source_id: str
    text: str
    source_hash: str
    language: str
    reality_key: str
    authority_kind: str
    provenance_id: str


@dataclass(frozen=True, slots=True)
class MathSpan:
    span_id: str
    text: str
    source_start: int
    source_end: int
    span_kind: str
    probability: float


@dataclass(frozen=True, slots=True)
class TypedFormalCandidate:
    expression: FormalExpression
    type_code: str
    bound_variables: tuple[str, ...]
    probability: float
    margin: float
    canonical_hash: str


@dataclass(frozen=True, slots=True)
class CompiledMathBody:
    body_id: str
    reality_key: str
    left: FormalExpression
    right: FormalExpression
    direction_policy: str
    registry_axiom_id: str | None
    provenance_hash: str
    body_hash: str


@dataclass(frozen=True, slots=True)
class MathCompilationEvidence:
    source_id: str
    statement_kind: str
    candidates: tuple[TypedFormalCandidate, ...]
    minimum_probability: float
    minimum_margin: float
    exact_checks: tuple[str, ...]
    failed_checks: tuple[str, ...]
    evidence_hash: str


@dataclass(frozen=True, slots=True)
class CompiledMathStatement:
    source: MathLanguageSource
    body: CompiledMathBody | None
    mumbrane_program: object | None
    disposition: str
    activation_state: str
    evidence: MathCompilationEvidence
    failure_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CompiledMathQuestion:
    source: MathLanguageSource
    source_expression: FormalExpression | None
    goal_expression: FormalExpression | None
    theorem_problem: TheoremProblem | None
    disposition: str
    evidence: MathCompilationEvidence
    failure_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MathRealityTransaction:
    transaction_id: str
    reality_key: str
    body_ids: tuple[str, ...]
    old_manifest_hash: str
    new_manifest_hash: str | None
    disposition: str


@dataclass(frozen=True, slots=True)
class L2InferenceResult:
    question: CompiledMathQuestion
    proof_result: object | None
    replay_valid: bool
    proof_hash: str | None
    authorized_answer: str | None
    disposition: str
    failure_codes: tuple[str, ...]
