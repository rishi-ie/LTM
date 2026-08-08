"""Permanent I1 report and mechanical classification."""

from __future__ import annotations

import json
from pathlib import Path


def write_report(workspace: Path, destination: Path) -> None:
    locked = json.loads((workspace / "locked-results.json").read_text(encoding="utf-8"))
    development = json.loads((workspace / "development-results.json").read_text(encoding="utf-8"))
    dev_metrics = development["metrics"]
    if dev_metrics.get("one_step_exactness", 0.0) < .90 or dev_metrics.get("accepted_precision", 0.0) < .95:
        classification = "I1-B — BODY REPRESENTATION FAILURE"
    elif locked["incorrect_accepted"] > 0:
        classification = "I1-C — ASSOCIATIVE-ONLY FAILURE"
    elif locked.get("energy_increase_count", 0) > 0:
        classification = "I1-D — LATENT DYNAMICS FAILURE"
    elif locked["safe_coverage"] < .85:
        classification = "I1-F — SAFE BUT LOW COVERAGE"
    else:
        classification = "I1-A — CONTROLLED RELATION-FREE LATENT INFERENCE PASS"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(f"""# I1 — Relation-Free Mumbrane Latent Inference

## Classification

**{classification}**

This experiment tests supplied atomic Mumbranes and a compact learned energy
field. It does not test raw text segmentation, factual insertion, or unrestricted
language reasoning. Historical G2 and LTM-I1 results are unchanged.

## Measured results

| Metric | Development | Locked |
| --- | ---: | ---: |
| Cases | {development['metrics']['cases']} | {locked['cases']} |
| Accepted precision | {development['metrics']['accepted_precision']:.4f} | {locked['accepted_precision']:.4f} |
| Safe coverage | {development['metrics']['safe_coverage']:.4f} | {locked['safe_coverage']:.4f} |
| All-case exactness | {development['metrics']['all_case_exactness']:.4f} | {locked['all_case_exactness']:.4f} |
| Incorrect accepted | {development['metrics']['incorrect_accepted']} | {locked['incorrect_accepted']} |
| One-step exactness | {development['metrics'].get('one_step_exactness', 0.0):.4f} | {locked.get('one_step_exactness', 0.0):.4f} |
| Energy increases | {development['metrics'].get('energy_increase_count', 0)} | {locked.get('energy_increase_count', 0)} |
| Runtime seconds | — | {locked.get('runtime_seconds', 0.0):.2f} |

The evaluator compares the latent candidate with hidden semantic gold. Runtime
receives no relation labels, logical closure, or evaluator path. Every result
emits an empty factual-operation tuple.

## Interpretation

The first failed boundary is the stored-body kernel: development one-step
exactness is below the required 0.90 gate, and cross-body chains do not compose.
This is therefore a representation failure, not evidence that the latent field
is safe for reasoning. The naturalistic MiniLM panel is diagnostic only.

Intervention artifact: `{workspace / 'intervention-results.json'}`.

## Next boundary

A pass authorizes an I2 experiment for a simple raw-data compiler and a verified
latent-candidate handoff. It does not replace G6/G9 or permit latent candidates
to become factual field state.
""", encoding="utf-8")
