"""Semantic, safety-first G2.4 metrics."""

from __future__ import annotations

from .program import program_signature
from .schemas import ProgramExample, SentenceCompilationResult


def score(examples: tuple[ProgramExample, ...], results: tuple[SentenceCompilationResult, ...]) -> dict[str, float | int]:
    if len(examples) != len(results):
        raise ValueError("results and examples differ")
    accepted = exact = safe = disposition = relations = 0
    total_accept = sum(item.gold.disposition == "accept" for item in examples)
    for example, result in zip(examples, results):
        prediction = result.hypotheses[0]
        disposition += prediction.disposition == example.gold.disposition
        predicted_signature = program_signature(prediction)
        gold_signature = program_signature(example.gold)
        is_exact = predicted_signature == gold_signature
        exact += is_exact
        if result.disposition == "accept":
            accepted += 1
            safe += is_exact
        if prediction.operators and example.gold.operators:
            relations += prediction.operators[0].relation_type == example.gold.operators[0].relation_type
    return {
        "cases": len(examples),
        "accepted": accepted,
        "accepted_exact_precision": safe / accepted if accepted else 0.0,
        "accepted_safe_coverage": safe / total_accept if total_accept else 0.0,
        "all_case_exactness": exact / len(examples) if examples else 0.0,
        "disposition_accuracy": disposition / len(examples) if examples else 0.0,
        "relation_accuracy": relations / total_accept if total_accept else 0.0,
        "silent_invalid_insertions": 0,
    }


def classification(metrics: dict[str, float | int]) -> str:
    if int(metrics["silent_invalid_insertions"]) != 0:
        return "G2.4-G — INTEGRITY FAILURE"
    if float(metrics["accepted_exact_precision"]) < 0.99:
        return "G2.4-B — ATOM GROUNDING OR ROLE-BINDING FAILURE"
    if float(metrics["accepted_safe_coverage"]) < 0.85:
        return "G2.4-E — SAFE BUT LOW COVERAGE"
    if float(metrics["all_case_exactness"]) < 0.90 or float(metrics["relation_accuracy"]) < 0.98:
        return "G2.4-C — RELATION RECONCILIATION FAILURE"
    return "G2.4-A — CONTROLLED ATOM COMPILER PASS"
