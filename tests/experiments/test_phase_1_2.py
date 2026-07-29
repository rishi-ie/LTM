"""Locked-fixture and deterministic Phase 1.2 selection checks."""

import json
from pathlib import Path

from ltm_poc.experiments.phase_1_2 import _grid, _select


def test_equilibrium_suite_is_balanced_static_and_weighted() -> None:
    payload = json.loads(
        Path("eval/phase-1.2/held-out.json").read_text(encoding="utf-8")
    )
    assert payload["locked"] is True
    assert len(payload["domains"]) == 24
    cases = [
        (domain, case) for domain in payload["domains"] for case in domain["cases"]
    ]
    assert len(cases) == 120
    counts: dict[str, int] = {}
    for domain, case in cases:
        counts[case["category"]] = counts.get(case["category"], 0) + 1
        relevant = set(case["high"]) | set(case["low"])
        assert len(relevant) >= 3
        assert relevant <= set(domain["documents"])
        distractors = set(domain["documents"]) - relevant
        assert len(distractors) >= 8
        for chunk_id in relevant:
            metadata = domain["documents"][chunk_id]["metadata"]
            assert {"priority", "confidence", "authority", "recency"} <= set(metadata)
        assert case["query"] not in {
            item["text"] for item in domain["documents"].values()
        }
    assert set(counts.values()) == {24}


def test_grid_has_18_configs_and_selection_uses_registered_order() -> None:
    assert len(_grid()) == 18
    base = {
        "summary": {
            "worst_high_weight_residual": 0.2,
            "average_weighted_residual": 0.1,
            "prompt_cosine": 0.9,
            "approximation_error": 0.01,
            "latency_ms": 1.01,
        },
        "config": {
            "max_weight": 0.5,
            "query_anchor": 1.0,
            "beta": 5.0,
        },
    }
    noisy = {
        "summary": {**base["summary"], "latency_ms": 1.04},
        "config": {**base["config"], "beta": 10.0},
    }
    assert _select([noisy, base])["config"]["beta"] == 5.0
