"""Immutable L3 contracts."""

from __future__ import annotations

from dataclasses import dataclass

from ltm_inference_i3.schemas import FormalExpression, TheoremProblem


@dataclass(frozen=True, slots=True)
class L3Source:
    source_id: str
    text: str
    source_hash: str
    reality_key: str
    provenance_id: str


@dataclass(frozen=True, slots=True)
class L3Body:
    body_id: str
    reality_key: str
    left: FormalExpression
    right: FormalExpression
    axiom_id: str | None
    direction_policy: str
    source_text: str
    source_hash: str
    body_hash: str
    mumbrane_program: object


@dataclass(frozen=True, slots=True)
class L3Question:
    source: L3Source
    source_expression: FormalExpression | None
    goal_expression: FormalExpression | None
    theorem_problem: TheoremProblem | None
    disposition: str
    failure_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MathCorpusManifest:
    reality_key: str
    body_count: int
    field_size: int
    sha256: str
    source_archive_hash: str


@dataclass(frozen=True, slots=True)
class ShortestProofCertificate:
    case_id: str
    source_hash: str
    goal_hash: str
    shortest_depth: int
    proof_body_ids: tuple[str, ...]
    certificate_hash: str


@dataclass(frozen=True, slots=True)
class L3Problem:
    case_id: str
    panel: str
    question: L3Question
    expected_depth: int
    certificate: ShortestProofCertificate
    body_ids: tuple[str, ...]
    bodies: tuple[L3Body, ...]


@dataclass(frozen=True, slots=True)
class L3LockedSuite:
    """Frozen public inputs and evaluator-only expectations for one L3 attempt.

    ``problems`` intentionally carry only the source, goal, and public field
    identities needed by the runtime.  Expected depth and proof-path details
    stay in the separate evaluator records written beside the suite.
    """

    bodies: tuple[L3Body, ...]
    grounded: tuple[L3Problem, ...]
    mixed: tuple[L3Problem, ...]
    safety: tuple[L3Problem, ...]
    suite_hash: str


@dataclass(frozen=True, slots=True)
class L3EvaluatorExpectation:
    case_id: str
    panel: str
    expected_disposition: str
    expected_depth: int | None
    required_body_ids: tuple[str, ...]
    certificate_hash: str


@dataclass(frozen=True, slots=True)
class L3Observation:
    case_id: str
    panel: str
    disposition: str
    proof_steps: int
    proof_valid: bool
    compiler_valid: bool
    bodies_opened: int
    states_explored: int
    runtime_ms: float
    failure_code: str
    proof_body_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class L3Result:
    classification: str
    grounded_success: float
    mixed_success: float
    accepted_precision: float
    proof_replay: float
    observations: tuple[L3Observation, ...]
