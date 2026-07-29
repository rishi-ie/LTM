"""Phase 1.1 fixture and deterministic selection checks."""

import json
from pathlib import Path

from ltm_poc.experiments.phase_1_1 import _selected


def test_held_out_fixture_is_balanced_and_locked() -> None:
    path = Path("eval/phase-1.1/held-out.json")
    scenarios = json.loads(path.read_text(encoding="utf-8"))
    assert len(scenarios) == 20
    assert sum(len(scenario["queries"]) for scenario in scenarios) == 100
    counts: dict[str, int] = {}
    all_documents = {
        doc_id for scenario in scenarios for doc_id in scenario["documents"]
    }
    for scenario in scenarios:
        counts[scenario["category"]] = counts.get(scenario["category"], 0) + len(
            scenario["queries"]
        )
        assert len(scenario["gold"]) >= 2
        assert set(scenario["gold"]) <= set(scenario["documents"])
        assert len(all_documents - set(scenario["gold"])) >= 8
    assert set(counts.values()) == {20}


def test_grid_selection_ignores_sub_tenth_millisecond_noise() -> None:
    base = {
        "summary": {
            "recall_at_4": 0.8,
            "precision_at_4": 0.4,
            "latency_ms": 1.01,
        },
        "config": {
            "slots": 4,
            "diversity_weight": 0.25,
            "similarity_cap": 0.60,
        },
    }
    noisy = {
        "summary": {**base["summary"], "latency_ms": 1.04},
        "config": {**base["config"], "similarity_cap": 0.75},
    }
    assert _selected([noisy, base])["config"]["similarity_cap"] == 0.60
