"""Measured I2.1 report and mechanical classification."""

from __future__ import annotations

import json
from pathlib import Path


def write_report(workspace: Path, destination: Path) -> None:
    development = json.loads((workspace / "development-results.json").read_text())
    gates = json.loads((Path(__file__).resolve().parents[2] / "configs/ltm-inference-i21.json").read_text())["gates"]
    diagnostics = development["diagnostics"]
    metrics = development["metrics"]
    if diagnostics["source_body_recall_at_64"] < gates["alignment_recall_at_64"]:
        classification = "I2.1-B — COORDINATE ALIGNMENT FAILURE"
    elif diagnostics["one_step_exactness"] < gates["one_step_exactness"]:
        classification = "I2.1-C — LOCAL TRANSITION FAILURE"
    elif metrics["required_body_frontier_recall"] < gates["frontier_recall_at_64"]:
        classification = "I2.1-D — MINIMAP RETRIEVAL FAILURE"
    elif metrics["accepted_precision"] < gates["accepted_precision"] or metrics["safe_coverage"] < gates["safe_coverage"]:
        classification = "I2.1-E — DYNAMIC COMPOSITION FAILURE"
    else:
        classification = "I2.1-A — ALIGNED TERMINAL-COMPLETION PASS"
    locked = json.loads((workspace / "locked-results.json").read_text()) if (workspace / "locked-results.json").exists() else None
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(f"""# I2.1 — Aligned Transition and Minimap Navigation Audit

## Classification

**{classification}**

## Development evidence

| Metric | Result |
| --- | ---: |
| Source-body recall@64 | {diagnostics['source_body_recall_at_64']:.4f} |
| One-step exactness | {diagnostics['one_step_exactness']:.4f} |
| Required-body frontier recall | {metrics['required_body_frontier_recall']:.4f} |
| Accepted precision | {metrics['accepted_precision']:.4f} |
| Safe coverage | {metrics['safe_coverage']:.4f} |
| Answerable exactness | {metrics['answerable_exactness']:.4f} |
| Incorrect accepted | {metrics['incorrect_accepted']} |

The experiment tests terminal completion only: the public prompt carries no
answer ID or hidden hop count. It ends when no compatible observed transition
remains. Runtime uses no G1 relation names, roles, closure, supplied candidate
list, or factual operations.

Locked result: `{json.dumps(locked, sort_keys=True) if locked else 'not authorized after development gate'}`.
""", encoding="utf-8")
