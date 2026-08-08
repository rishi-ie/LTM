"""Measured G2.9 report writer; never fills in unexecuted stages."""

from __future__ import annotations

import json
from pathlib import Path


def write_report(workspace: Path, destination: Path) -> None:
    result_path = next((item for item in (workspace / "locked-results.json", workspace / "kernel-results.json", workspace / "kernel-development-results.json") if item.exists()), None)
    result = json.loads(result_path.read_text(encoding="utf-8")) if result_path else {}
    lines = [
        "# G2.9 — Post-Attention Golden-Query Topology Compiler", "",
        f"**Classification: {result.get('classification', 'NOT-RUN')}**", "",
        "G2.9 tests a focused replacement routing kernel: contextual MiniLM states are compared after self-attention with dynamically re-encoded, G1-derived golden operator and role queries. Sparse G1 operations remain factual authority; FieldIR vectors and attention deltas are sidecars only.", "",
        "## Measured result", "", "| Metric | Value |", "|---|---:|",
    ]
    lines.extend(f"| {key} | {value} |" for key, value in sorted(result.get("metrics", {}).items()))
    lines.extend(["", "## Scope boundary", "", "The experiment is fail-fast. A failed gold-content kernel does not support claims about span extraction, identity resolution, document composition, AtomBank migration, or G3–G9 integration. A kernel-only result cannot replace the adopted G2.5 engineering baseline.", "", "The dynamic bank is encoded with the same evolving encoder checkpoint after each optimizer update. It avoids static-anchor coordinate drift and uses exact G1 structural cards instead of hash-derived structural vectors."])
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
