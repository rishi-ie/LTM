from __future__ import annotations

from collections import Counter

from .schemas import IntegrationResult


def summarize(results: tuple[IntegrationResult, ...]) -> dict[str, object]:
    total = len(results) or 1
    metrics = {
        "cases": len(results),
        "semantic_agreement": sum(item.semantic_equal for item in results) / total,
        "artifact_agreement": sum(item.artifact_equal for item in results) / total,
        "projection_agreement": sum(item.projection_equal for item in results) / total,
        "address_agreement": sum(item.address_equal for item in results) / total,
        "frontier_agreement": sum(item.frontier_equal for item in results) / total,
        "coverage_agreement": sum(item.coverage_equal for item in results) / total,
        "hard_agreement": sum(item.hard_equal for item in results) / total,
        "soft_agreement": sum(item.soft_equal for item in results) / total,
        "g9_agreement": sum(item.g9_equal for item in results) / total,
        "decoder_agreement": sum(item.decoder_equal for item in results) / total,
        "vector_rows_read": sum(item.vector_rows for item in results),
        "failures": sum(bool(item.failure_codes) for item in results),
    }
    return {"metrics": metrics, "failure_codes": dict(Counter(code for item in results for code in item.failure_codes))}
