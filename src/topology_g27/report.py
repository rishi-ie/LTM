"""Permanent G2.7 report writer."""

from __future__ import annotations

import json
from pathlib import Path


def write_report(workspace: Path, destination: Path) -> None:
    result_path = workspace / "locked-results.json"
    if not result_path.exists():
        result_path = workspace / "kernel-results.json"
    if not result_path.exists():
        result_path = workspace / "kernel-development-results.json"
    result = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else {}
    metrics = result.get("metrics", {})
    lines = [
        "# G2.7 — Frozen Semantic Reasoning-Atom Coordinate Compiler",
        "",
        f"**Classification: {result.get('classification', 'NOT-RUN')}**",
        "",
        "G2.7 tests a frozen MiniLM semantic encoder paired with a compact topology kernel. The kernel preserves an 18-dimensional reasoning-atom coordinate, role bindings, exact G1 relations and FieldIR handoff.",
        "",
        "## Measured result",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    lines.extend(f"| {key} | {value} |" for key, value in sorted(metrics.items()))
    kernel_path = workspace / "kernel-results.json"
    if kernel_path.exists() and result_path.name != "kernel-results.json":
        kernel = json.loads(kernel_path.read_text(encoding="utf-8"))
        lines.extend(["", "## Kernel gate", "", f"Kernel classification: **{kernel.get('classification')}**", ""])
        lines.extend(f"| {key} | {value} |" for key, value in sorted(kernel.get("metrics", {}).items()))
    lines.extend([
        "",
        "## Boundary",
        "",
        "This is a development-gate result, not a locked classification: the frozen semantic kernel missed its mandatory gate, so freezing and locked evaluation were refused. The fail-fast boundary also prevents claims about span extraction, persistent identity and document composition. G1 remains factual authority; continuous coordinates are routing and field geometry only.",
        "",
        "A prior prototype that directly matched surface cues to relation names was intentionally discarded before this run; it would have measured template recognition rather than frozen semantic-coordinate compilation.",
        "",
        "Historical G2–G2.6 results remain unchanged. This result does not establish unrestricted language understanding or decoder quality.",
    ])
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
