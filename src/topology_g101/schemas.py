from __future__ import annotations

from dataclasses import dataclass

from topology_g10.schemas import DecoderBundle


@dataclass(frozen=True, slots=True)
class AnswerMR:
    bundle_id: str
    disposition: str
    status: str
    claim_ids: tuple[str, ...]
    mandatory_disclosures: tuple[str, ...]
    style: str


@dataclass(frozen=True, slots=True)
class SurfaceCandidate:
    bundle_id: str
    template_id: str
    text: str
    covered_claim_ids: tuple[str, ...]
    disclosures: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RankedRealization:
    bundle_id: str
    answer_mr: AnswerMR
    selected: SurfaceCandidate
    candidates: tuple[SurfaceCandidate, ...]
    score: float
    validator_accepted: bool


def answer_mr(bundle: DecoderBundle) -> AnswerMR:
    disclosures: list[str] = []
    if bundle.conflicts:
        disclosures.append("conflict")
    if bundle.assumptions:
        disclosures.append("scope" if any("fictional scope" in item.lower() for item in bundle.assumptions) else "partial")
    if bundle.status == "unknown":
        disclosures.append("abstention")
    return AnswerMR(bundle.bundle_id, bundle.required_disposition, bundle.status, tuple(item.claim_id for item in bundle.authorized_claims), tuple(disclosures), bundle.state.style)
