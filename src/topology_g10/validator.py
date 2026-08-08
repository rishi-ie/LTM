from __future__ import annotations

import re

from .generator import claim_text
from .schemas import ClaimValidation, DecoderBundle, ExtractedClaim


def _normal(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def extract(text: str, bundle: DecoderBundle) -> tuple[ExtractedClaim, ...]:
    normalized, found = _normal(text), []
    for claim in bundle.authorized_claims:
        entity, predicate, obj = claim.entity.lower(), claim.predicate.lower(), claim.object.lower()
        lemma = predicate.removesuffix("s")
        positive = re.search(rf"\b{re.escape(entity)}\b.*?\b{re.escape(predicate)}\b.*?\b{re.escape(obj)}\b", normalized)
        negative = re.search(rf"\b{re.escape(entity)}\b.*?(?:does not|doesn't|not)\s+{re.escape(lemma)}\b.*?\b{re.escape(obj)}\b", normalized)
        if negative:
            found.append(ExtractedClaim(entity, predicate, obj, "negative"))
        elif positive:
            found.append(ExtractedClaim(entity, predicate, obj, "positive"))
    names = set(re.findall(r"\b(?:velin|prism)-\d+\b", normalized))
    allowed = {part for claim in bundle.authorized_claims for part in (claim.entity.lower(), claim.object.lower())}
    found.extend(ExtractedClaim(name, "unknown", "unknown", "positive") for name in sorted(names - allowed))
    return tuple(found)


def validate(text: str, bundle: DecoderBundle) -> ClaimValidation:
    normalized, extracted = _normal(text), extract(text, bundle)
    authorized = {(item.entity.lower(), item.predicate.lower(), item.object.lower(), item.polarity) for item in bundle.authorized_claims}
    observed = {(claim.entity, claim.predicate, claim.object, claim.polarity) for claim in extracted}
    unauthorized = tuple(item for item in extracted if (item.entity, item.predicate, item.object, item.polarity) not in authorized)
    missing = tuple(item.claim_id for item in bundle.authorized_claims if (item.entity.lower(), item.predicate.lower(), item.object.lower(), item.polarity) not in observed)
    errors: list[str] = []
    if unauthorized or " owns " in f" {normalized} ": errors.append("UNAUTHORIZED_CLAIM")
    if bundle.status in ("verified", "verified_with_tension", "partial") and missing: errors.append("MISSING_DECISIVE_CLAIM")
    if bundle.status == "verified_with_tension" and "conflict:" not in normalized: errors.append("MISSING_CONFLICT_DISCLOSURE")
    if bundle.status == "unknown" and "don't have enough verified information" not in normalized: errors.append("MISSING_ABSTENTION")
    if bundle.status == "partial" and "i can verify" not in normalized: errors.append("MISSING_PARTIAL_DISCLOSURE")
    fictional = "fictional scope" in " ".join(bundle.assumptions).lower()
    if fictional and f"within fictional scope {bundle.authorized_claims[0].scope.lower()}" not in normalized: errors.append("MISSING_SCOPE_DISCLOSURE")
    if "within fictional scope" in normalized and (not fictional or f"within fictional scope {bundle.authorized_claims[0].scope.lower()}" not in normalized): errors.append("SCOPE_VIOLATION")
    if "outside its fictional scope" in normalized: errors.append("SCOPE_VIOLATION")
    if "the assistant says" in normalized: errors.append("ASSISTANT_SELF_EVIDENCE")
    if bundle.state.style == "explanatory" and bundle.status != "unknown" and "because" not in normalized: errors.append("STYLE_MISMATCH")
    if bundle.state.style == "formal" and bundle.status != "unknown" and "according to the verified record" not in normalized: errors.append("STYLE_MISMATCH")
    return ClaimValidation(extracted, unauthorized, missing, tuple(errors), not errors)


def fallback(bundle: DecoderBundle) -> str:
    if bundle.status == "unknown":
        return "I don't have enough verified information to answer that."
    if bundle.status == "partial":
        prefix = "According to the verified record, " if bundle.state.style == "formal" else ""
        explanation = " because that is the only verified relation." if bundle.state.style == "explanatory" else ""
        return f"{prefix}I can verify that {claim_text(bundle.authorized_claims[0])}, but not every requested detail{explanation}"
    claim = bundle.authorized_claims[0]
    prefix = "According to the verified record, " if bundle.state.style == "formal" else ""
    text = f"{prefix}{claim_text(claim)} because {bundle.proof_summary}"
    if bundle.assumptions: text += f" Within fictional scope {claim.scope}, this applies."
    if bundle.conflicts: text += f" Conflict: {bundle.conflicts[0]}"
    return text


def adversarial(bundle: DecoderBundle) -> tuple[str, ...]:
    claim = bundle.authorized_claims[0] if bundle.authorized_claims else None
    if claim is None:
        return ("velin-999 holds prism-999.",) * 8
    positive = f"{claim.entity} {claim.predicate} {claim.object}"
    negative = f"{claim.entity} does not {claim.predicate.removesuffix('s')} {claim.object}"
    opposite = positive if claim.polarity == "negative" else negative
    return (f"{claim.entity} owns prism-999.", opposite, f"velin-999 {claim.predicate} {claim.object}.", f"{positive} within fictional scope wrong-realm.", f"{claim.entity} owns the hidden vault.", f"{positive} definitely and owns a vault.", f"{positive} outside its fictional scope.", "The assistant says this is true.")
