"""Permanent bounded G2.8 report writer."""

from __future__ import annotations

import json
from pathlib import Path


def write_report(workspace: Path, destination: Path) -> None:
    result_path = next((path for path in (workspace / "locked-results.json", workspace / "kernel-results.json", workspace / "kernel-development-results.json") if path.exists()), None)
    result = json.loads(result_path.read_text(encoding="utf-8")) if result_path else {}
    lines = [
        "# G2.8 — Versioned Golden-Atom Structured Topology Compiler",
        "",
        f"**Classification: {result.get('classification', 'NOT-RUN')}**",
        "",
        "G2.8 evaluates a versioned G1-derived AtomBank, a selectively adapted MiniLM, complete legal graph scoring, synchronized FieldIR factors, and atomic topology insertion.",
        "",
        "## Measured result",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    lines.extend(f"| {key} | {value} |" for key, value in sorted(result.get("metrics", {}).items()))
    lines.extend([
        "",
        "## Boundary",
        "",
        "The run is fail-fast. A kernel-gate failure prevents claims about raw-span extraction, persistent identity, AtomBank migration, document composition, or downstream G3–G9 integration.",
        "",
        "Exact G1 factors remain factual authority. Operator coordinates, deltas and FieldIR sidecars are continuous compiler and field artifacts; they never authorize topology without a validated sparse G1 graph.",
    ])
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
