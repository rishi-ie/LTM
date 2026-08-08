"""Small deterministic metrics for the G2.11 fail-fast stages."""

from __future__ import annotations

from collections.abc import Iterable

from .dataset import AtomicExample
from .schemas import AtomicFieldPatch


def score_examples(examples: Iterable[AtomicExample], patches: Iterable[AtomicFieldPatch]) -> dict[str, float | int]:
    rows = tuple(zip(examples, patches, strict=True))
    accepted = tuple((example, patch) for example, patch in rows if patch.disposition == "accept")
    exact = sum(patch.relation_types == ((example.relation_type,) if example.relation_type else ()) for example, patch in accepted)
    safe = sum(
        (example.disposition != "accept" and patch.disposition != "accept")
        or (example.disposition == "accept" and patch.relation_types == (example.relation_type,))
        for example, patch in rows
    )
    severe = sum(
        example.disposition == "accept"
        and patch.disposition == "accept"
        and patch.relation_types != (example.relation_type,)
        for example, patch in rows
    )
    return {
        "cases": len(rows),
        "accepted": len(accepted),
        "accepted_exact": exact,
        "accepted_precision": exact / len(accepted) if accepted else 1.0,
        "safe_cases": safe,
        "safe_coverage": safe / len(rows) if rows else 1.0,
        "all_case_exactness": safe / len(rows) if rows else 1.0,
        "severe_errors": severe,
    }

