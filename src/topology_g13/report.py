from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def report(workspace: Path) -> dict:
    result = json.loads((workspace / "locked-results.json").read_text())
    metrics = result["metrics"]
    text = f"""# G13 — 1M-to-100M Context Scale Report

## Mechanical classification

**{result['classification']}**

## Measured result

| Measure | Result |
| --- | ---: |
| Cross-scale conclusion agreement | {metrics['conclusion_agreement']:.4f} |
| Required-factor recall | {metrics['required_factor_recall']:.4f} |
| S4 physical-layout agreement | {metrics['layout_agreement']} |
| S4 warm p95 core latency | {metrics['p95_warm_core_ms']:.3f} ms |
| Maximum opened factor fraction | {metrics['max_factor_fraction']:.8f} |
| Peak RSS | {metrics['peak_rss_mb']:.2f} MB |
| Total locked runtime | {metrics['runtime_seconds']:.2f} s |

## Exact claim boundary

This run stored the registered source as actual `uint32` token IDs and materialized
fixed-width factor records on disk through the 100M-token / 25M-factor scale. It
ran a controlled adapter chain for typed addressing, bounded frontier selection,
coverage widening, G6 hard propagation, G7 soft reconciliation, G8 batch-order
invariance, independent hard replay, and session-overlay checks.

The query-relevant typed factors are deliberately held in the common S1 prefix;
the added S2–S4 factors are addressable persistent distractors. Thus this is a
definitive test of sparse access, physical storage, and preservation of the
registered core contracts under a 100M-token field. It is not evidence that the
unresolved G2 compiler can ingest arbitrary 100M-token natural-language context,
nor that arbitrary far-field semantic influences are covered.
"""
    path = ROOT / "docs" / "experiments" / "gaps" / "g13" / "report.md"
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text)
    return {"classification": result["classification"], "report": str(path)}
