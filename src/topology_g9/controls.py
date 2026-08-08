from __future__ import annotations

from .schemas import CandidateBundle, VerificationResult, text_hash
from .verifier import verify


def hash_only(bundle: CandidateBundle) -> VerificationResult:
    valid = all(text_hash(source.text) == source.content_hash for source in bundle.sources)
    return VerificationResult(bundle.bundle_id, "verified" if valid else "rejected", bundle.target_literal if valid else None, (), (), (), () if valid else ("SOURCE_HASH_MISMATCH",), ("hash",))


def energy_threshold(bundle: CandidateBundle) -> VerificationResult:
    valid = bundle.soft.final_energy <= 1.0 and bundle.confidence >= .90
    return VerificationResult(bundle.bundle_id, "verified" if valid else "rejected", bundle.target_literal if valid else None, (), (), (), () if valid else ("ENERGY_THRESHOLD",), ("reported_energy",))


def no_coverage(bundle: CandidateBundle) -> VerificationResult:
    return verify(bundle, verify_coverage=False)


def self_critique(bundle: CandidateBundle) -> VerificationResult:
    return VerificationResult(bundle.bundle_id, "verified" if bundle.self_claimed_valid else "rejected", bundle.target_literal if bundle.self_claimed_valid else None, (), (), (), (), ("candidate_claim",))
