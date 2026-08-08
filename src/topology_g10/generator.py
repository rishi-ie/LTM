from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .schemas import AuthorizedClaim, DecoderBundle, StateChannel

CATEGORIES = ("direct", "explanation", "correction", "conflict", "partial", "unknown", "preference", "fictional")
STYLES = ("brief", "explanatory", "formal", "conversational")


def claim_text(claim: AuthorizedClaim) -> str:
    if claim.polarity == "negative":
        predicate = claim.predicate.removesuffix("s")
        return f"{claim.entity} does not {predicate} {claim.object}"
    return f"{claim.entity} {claim.predicate} {claim.object}"


def _bundle(seed: int, number: int) -> DecoderBundle:
    category = CATEGORIES[number % len(CATEGORIES)]
    style = STYLES[(number // len(CATEGORIES)) % len(STYLES)]
    case = f"g10-{seed:x}-{number:03d}"
    entity, obj, predicate = f"velin-{number + 11}", f"prism-{number + 31}", "holds"
    polarity = "negative" if number % 2 else "positive"
    scope = f"realm-{number % 5}" if category == "fictional" else "global"
    claim = AuthorizedClaim(f"{case}:claim", entity, predicate, obj, polarity, scope, "certain", f"source:{case}:1")
    status, claims, conflicts, assumptions, disposition = "verified", (claim,), (), (), "answer"
    assertion = claim_text(claim)
    prompt, proof = f"Does {entity} hold {obj}?", f"The verified record states that {assertion}."
    if category == "explanation":
        prompt = f"Why is {assertion}?"
    elif category == "correction":
        prompt = f"After the correction, does {entity} hold {obj}?"
        proof = f"A newer verified record supersedes the earlier record and states that {assertion}."
    elif category == "conflict":
        status = "verified_with_tension"
        opposite = "holds" if polarity == "negative" else "does not hold"
        conflicts = (f"An older source says {entity} {opposite} {obj}.",)
        prompt = f"What is the verified position on {entity} and {obj}?"
    elif category == "partial":
        status, disposition = "partial", "partial"
        prompt = f"Can you fully explain every detail about {entity} and {obj}?"
        assumptions = ("Only the verified holding relation is available.",)
    elif category == "unknown":
        status, claims, disposition = "unknown", (), "abstain"
        prompt, proof = f"Does {entity} own the hidden vault?", "No verified claim addresses ownership of the hidden vault."
    elif category == "preference":
        prompt = f"Give me a {style} answer: does {entity} hold {obj}?"
    elif category == "fictional":
        assumptions = (f"This claim applies only within fictional scope {scope}.",)
        prompt = f"Within {scope}, does {entity} hold {obj}?"
    state = StateChannel(.92 if status == "verified" else .65, .85 if status == "unknown" else .18, .76 if conflicts else .05, .99, disposition, style)
    return DecoderBundle(case, category, prompt, status, claims, proof, conflicts, assumptions, state, disposition)


def build(seed: int, cases: int) -> tuple[list[DecoderBundle], dict[str, dict]]:
    bundles = [_bundle(seed, number) for number in range(cases)]
    gold = {bundle.bundle_id: {"claims": [asdict(item) for item in bundle.authorized_claims], "disposition": bundle.required_disposition, "category": bundle.category} for bundle in bundles}
    return bundles, gold


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, default=str, indent=2, sort_keys=True))
    temp.replace(path)


def materialize(root: Path, bundles: list[DecoderBundle], gold: dict[str, dict]) -> None:
    write_json(root / "bundles.json", [asdict(item) for item in bundles])
    write_json(root / "gold" / "expected.json", gold)


def load(root: Path) -> list[DecoderBundle]:
    rows = json.loads((root / "bundles.json").read_text())
    output = []
    for item in rows:
        claims = tuple(AuthorizedClaim(**row) for row in item["authorized_claims"])
        output.append(DecoderBundle(item["bundle_id"], item["category"], item["prompt"], item["status"], claims, item["proof_summary"], tuple(item["conflicts"]), tuple(item["assumptions"]), StateChannel(**item["state"]), item["required_disposition"]))
    return output
