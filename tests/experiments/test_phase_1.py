"""The pre-registered quality gates are deterministic."""

from ltm_poc.experiments.phase_1 import classify
from ltm_poc.experiments.phase_1_1 import _classify


def test_classification_requires_improvement_without_mean_shift_dominance() -> None:
    result_a = {
        "direct": {"recall_at_4": 0.70, "precision_at_4": 0.50, "latency_ms": 1.0},
        "mean_shift": {"recall_at_4": 0.72, "precision_at_4": 0.50, "latency_ms": 2.0},
        "latent": {"recall_at_4": 0.80, "precision_at_4": 0.48, "latency_ms": 1.5},
    }
    assert classify(result_a) == "A"
    result_a["latent"]["recall_at_4"] = 0.70
    assert classify(result_a) == "B"


def test_set_classifier_rejects_tiny_unreliable_gain() -> None:
    rows = []
    for index in range(100):
        direct = 1.0 if index < 88 else 0.0
        multi = 1.0 if index < 89 else 0.0
        for method, recall in (
            ("direct", direct),
            ("mmr", 0.75),
            ("multi_latent", multi),
        ):
            rows.append(
                {
                    "case_id": str(index),
                    "domain": f"d{index // 5}",
                    "method": method,
                    "recall_at_4": recall,
                    "precision_at_4": recall / 2,
                    "ids": [method],
                    "unit_norm": True,
                    "initial_energy": 0.0,
                    "final_energy": -1.0,
                    "set_evaluations": 9,
                }
            )
    assert _classify(rows)[0] == "B"
