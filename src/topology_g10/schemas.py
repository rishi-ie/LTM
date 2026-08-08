from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class AuthorizedClaim:
    claim_id: str
    entity: str
    predicate: str
    object: str
    polarity: str
    scope: str
    certainty: str
    provenance: str


@dataclass(frozen=True, slots=True)
class StateChannel:
    confidence: float
    uncertainty: float
    conflict_tension: float
    coverage: float
    response_act: str
    style: str


@dataclass(frozen=True, slots=True)
class DecoderBundle:
    bundle_id: str
    category: str
    prompt: str
    status: str
    authorized_claims: tuple[AuthorizedClaim, ...]
    proof_summary: str
    conflicts: tuple[str, ...]
    assumptions: tuple[str, ...]
    state: StateChannel
    required_disposition: str


@dataclass(frozen=True, slots=True)
class ExtractedClaim:
    entity: str
    predicate: str
    object: str
    polarity: str


@dataclass(frozen=True, slots=True)
class ClaimValidation:
    extracted_claims: tuple[ExtractedClaim, ...]
    unauthorized_claims: tuple[ExtractedClaim, ...]
    missing_claim_ids: tuple[str, ...]
    errors: tuple[str, ...]
    accepted: bool


@dataclass(frozen=True, slots=True)
class GenerationRecord:
    method: str
    original_text: str
    repair_text: str | None
    generated_tokens: int
    runtime_ms: float


@dataclass(frozen=True, slots=True)
class DecoderResult:
    bundle_id: str
    final_text: str
    validation: ClaimValidation
    generation: GenerationRecord
    fallback_used: bool
    disposition: str


def row(value: object) -> dict:
    return asdict(value)
