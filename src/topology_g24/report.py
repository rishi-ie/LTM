"""Permanent, bounded G2.4 report generation."""

from __future__ import annotations

import json
from pathlib import Path


def write_report(workspace: Path, destination: Path) -> None:
    results = json.loads((workspace / "locked-results.json").read_text(encoding="utf-8"))
    metrics = results["metrics"]
    lines = [
        "# G2.4 — Atom-Vector Topology Compiler Report",
        "",
        "## Result",
        "",
        f"**{results['classification']}**",
        "",
        "This run tests the controlled sentence-level compiler only. It does not establish unrestricted language ingestion, cross-document linking, decoder quality, or product readiness.",
        "",
        "## Locked measurements",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {key.replace('_', ' ')} | {value} |" for key, value in metrics.items())
    lines += ["", "## Boundary", "", "Accepted output is assembled only after G1 registry validation. Invalid output is quarantined rather than partially inserted.", ""]
    destination.write_text("\n".join(lines), encoding="utf-8")
