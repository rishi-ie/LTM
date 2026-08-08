"""Small frozen precision/coverage threshold selection."""

from __future__ import annotations


def select_threshold(metrics_by_threshold: tuple[tuple[float, float, dict[str, float]], ...], minimum_precision: float = 0.95) -> dict[str, float]:
    valid = [item for item in metrics_by_threshold if item[2].get("accepted_exact_precision", 0.0) >= minimum_precision and item[2].get("reversal_false_accepts", 1) == 0]
    if not valid:
        return {"confidence": 0.99, "margin": 0.30, "coverage": 0.0}
    confidence, margin, metrics = max(valid, key=lambda item: (item[2].get("safe_coverage", 0.0), -item[0], -item[1]))
    return {"confidence": confidence, "margin": margin, "coverage": metrics.get("safe_coverage", 0.0)}
