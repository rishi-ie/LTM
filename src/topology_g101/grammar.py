"""Finite semantic grammar: every emitted candidate is validator-safe by construction."""

from __future__ import annotations

from topology_g10.generator import claim_text
from topology_g10.schemas import DecoderBundle

from .schemas import AnswerMR, SurfaceCandidate


def _claim(bundle: DecoderBundle, index: int = 0) -> str:
    return claim_text(bundle.authorized_claims[index])


def _proof(bundle: DecoderBundle) -> str:
    return bundle.proof_summary.rstrip(".")


def candidates(bundle: DecoderBundle, mr: AnswerMR) -> tuple[SurfaceCandidate, ...]:
    claim_ids = tuple(item.claim_id for item in bundle.authorized_claims)
    rows: list[SurfaceCandidate] = []
    if mr.status == "unknown":
        rows = [
            SurfaceCandidate(bundle.bundle_id, "unknown-1", "I don't have enough verified information to answer that.", (), ("abstention",)),
            SurfaceCandidate(bundle.bundle_id, "unknown-2", "I don't have enough verified information to answer that, according to the verified record.", (), ("abstention",)),
        ]
    elif mr.disposition == "partial":
        suffix = " because that is the only verified relation." if mr.style == "explanatory" else ""
        prefix = "According to the verified record, " if mr.style == "formal" else ""
        rows = [
            SurfaceCandidate(bundle.bundle_id, "partial-1", f"{prefix}I can verify that {_claim(bundle)}, but not every requested detail{suffix}", claim_ids[:1], ("partial",)),
            SurfaceCandidate(bundle.bundle_id, "partial-2", f"{prefix}I can verify that {_claim(bundle)}, but not every requested detail{suffix}", claim_ids[:1], ("partial",)),
        ]
    else:
        claim = _claim(bundle)
        scope = f" Within fictional scope {bundle.authorized_claims[0].scope}, this applies." if "scope" in mr.mandatory_disclosures else ""
        conflict = f" Conflict: {bundle.conflicts[0]}" if "conflict" in mr.mandatory_disclosures else ""
        prefix = "According to the verified record, " if mr.style == "formal" else ""
        rows = [
            SurfaceCandidate(bundle.bundle_id, "claim-1", f"{prefix}{claim} because {_proof(bundle)}.{scope}{conflict}", claim_ids, tuple(mr.mandatory_disclosures)),
            SurfaceCandidate(bundle.bundle_id, "claim-2", f"{prefix}{claim} because {_proof(bundle)}.{scope}{conflict}", claim_ids, tuple(mr.mandatory_disclosures)),
        ]
    return tuple(rows)
