"""Permanent G2.6 report writer."""

from __future__ import annotations

import json
from pathlib import Path


def write_report(workspace: Path, destination: Path) -> None:
    result_path = workspace / "locked-results.json"
    if not result_path.exists():
        result_path = workspace / "development-results.json"
    result = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else {}
    metrics = result.get("metrics", {})
    classification = result.get("classification", "NOT-RUN")
    lines = [
        "# G2.6 — G1-Constrained Dual-Prototype Atom-Pair Compiler",
        "",
        "## Result",
        "",
        f"**Classification: {classification}**",
        "",
        "G2.6 tests a relation/role compiler using G1-derived structural prototypes, learned linguistic prototypes, ordered atom-pair scoring, and atomic FieldIR handoff. The continuous field remains advisory; G1 remains factual authority.",
        "",
        "## Development kernel measurements",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    for key, value in sorted(metrics.items()):
        lines.append(f"| {key} | {value} |")
    lines.extend([
        "",
        "## Boundary",
        "",
        "The run is fail-fast. The clean development kernel did not meet the relaxed 95% gate, so locked generation, span extraction, persistent identity, and document composition were not authorized. This report does not alter historical G2, G2.1, G2.3, G2.4, or G2.5 results.",
        "",
        "## Safety statement",
        "",
        "No invalid G1 insertion or unsafe accepted direction may be treated as acceptable merely because aggregate accuracy is high.",
    ])
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
