from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def report(workspace: Path) -> dict:
    value = json.loads((workspace / "locked-results.json").read_text())
    rows = []
    for name, result in value["methods"].items():
        metric = result["metrics"]
        rows.append(f"| {name} | {metric['relation_macro_f1']:.3f} | {metric['direction_accuracy']:.3f} | {metric['role_exact_accuracy']:.3f} | {metric['topology_agreement']:.3f} |")
    text = f"""# G2.1 — Frozen Reasoning Embedding Kernel Report

## Classification

**{value['classification']}**

This experiment used frozen local all-MiniLM-L6-v2 embeddings, supplied
proposition spans, a linear multi-head baseline and a nonlinear 128-dimensional
reasoning projection. It does not test clause extraction or general document
ingestion.

## Locked results

| Method | Relation macro F1 | Direction | Exact roles | G1 topology agreement |
| --- | ---: | ---: | ---: | ---: |
{chr(10).join(rows)}

Runtime: `{value['runtime_seconds']:.2f} s`; peak RSS: `{value['peak_rss_mb']:.2f} MB`.

## Boundary

An operational pass means a frozen semantic encoder plus a learned classifier
can compile supplied propositions into the registered controlled G1 relation
set. It does not establish natural-language clause extraction, unrestricted
topology compilation, latent optimization or large-context reliability.
"""
    (workspace / "g2-1-reasoning-embedder-report.md").write_text(text)
    (ROOT / "docs" / "g2-1-reasoning-embedder-report.md").write_text(text)
    return {"report": str(ROOT / "docs" / "g2-1-reasoning-embedder-report.md")}
