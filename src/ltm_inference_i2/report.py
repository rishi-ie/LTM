from __future__ import annotations

import json
from pathlib import Path


def write_report(workspace: Path, destination: Path) -> None:
    dev = json.loads((workspace / "development-results.json").read_text())
    locked = json.loads((workspace / "locked-results.json").read_text())
    verification = json.loads((workspace / "verification.json").read_text())
    if not verification.get("frozen_source_matches", False):
        classification = "I2-G — INTEGRITY FAILURE"
    elif dev["metrics"].get("by_depth", {}).get("1", 0.0) < .95:
        classification = "I2-C — LOCAL TRANSITION FAILURE"
    elif locked.get("incorrect_accepted", 0) > 0:
        classification = "I2-E — LATENT COMPOSITION FAILURE"
    elif locked.get("safe_coverage", 0.0) < .85:
        classification = "I2-S — SAFE BUT LOW COVERAGE"
    else:
        classification = "I2-A — MULTISCALE RELATION-FREE DYNAMIC FIELD PASS"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(f"""# I2 — Multiscale Minimap Latent Dynamic Inference

## Classification

**{classification}**

I2 tests supplied atomic Mumbranes, a fixed prompt anchor, a movable 128D
inference state, hierarchical minimap summaries, dynamic frontier reopening,
and unnamed learned transition sketches. Runtime receives no G1 relation names,
logical closure, proof labels, evaluator gold, or supplied candidate IDs.

## Results

| Metric | Development | Locked |
| --- | ---: | ---: |
| Cases | {dev['metrics']['cases']} | {locked['cases']} |
| Accepted precision | {dev['metrics']['accepted_precision']:.4f} | {locked['accepted_precision']:.4f} |
| Safe coverage | {dev['metrics']['safe_coverage']:.4f} | {locked['safe_coverage']:.4f} |
| Answerable exactness | {dev['metrics']['answerable_exactness']:.4f} | {locked['answerable_exactness']:.4f} |
| Required-body frontier recall | {dev['metrics']['required_body_frontier_recall']:.4f} | {locked['required_body_frontier_recall']:.4f} |
| Incorrect accepted | {dev['metrics']['incorrect_accepted']} | {locked['incorrect_accepted']} |
| Energy/step failures | {dev['metrics']['energy_increase_count']} | {locked['energy_increase_count']} |
| Runtime seconds | — | {locked.get('runtime_seconds', 0.0):.2f} |

Development depth results: `{json.dumps(dev['metrics'].get('by_depth', {}), sort_keys=True)}`.

## Interpretation

The result is a mechanism result for the supplied-Mumbrane boundary. It does
not establish raw-language compilation, factual insertion, unrestricted depth,
or decoder quality. Naturalistic MiniLM execution is diagnostic only. Every
runtime result emits an empty factual-operation tuple.

Authoritative workspace: `{workspace}`.
""", encoding="utf-8")
