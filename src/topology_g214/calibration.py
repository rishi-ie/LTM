from __future__ import annotations

from .evaluate import score
from .gate import gate_cases, regrade
from .schemas import GateCase


def choose_thresholds(model, cases: tuple[GateCase, ...], gates: dict[str, object]) -> tuple[dict[str, float], dict[str, object]]:
    base_results = gate_cases(model, cases, {"confidence": 0.0, "margin": 0.0, "identity_confidence": 0.0, "identity_margin": 0.0})
    best = None
    for confidence in (0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95):
        for margin in (0.02, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30):
            thresholds = {"confidence": confidence, "margin": margin, "identity_confidence": 0.70, "identity_margin": 0.05}
            metrics = score(cases, tuple(regrade(result, confidence_threshold=confidence, margin_threshold=margin, identity_confidence=thresholds["identity_confidence"], identity_margin=thresholds["identity_margin"]) for result in base_results))
            if metrics["incorrect_accepted_predictions"] == 0:
                key = (metrics["safe_coverage"], metrics["accepted_precision"], -confidence, -margin)
                if best is None or key > best[0]:
                    best = (key, thresholds, metrics)
    if best is None:
        thresholds = {"confidence": 0.95, "margin": 0.30, "identity_confidence": 0.70, "identity_margin": 0.05}
        return thresholds, score(cases, tuple(regrade(result, confidence_threshold=thresholds["confidence"], margin_threshold=thresholds["margin"], identity_confidence=thresholds["identity_confidence"], identity_margin=thresholds["identity_margin"]) for result in base_results))
    return best[1], best[2]
