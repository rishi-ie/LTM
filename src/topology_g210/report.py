"""Permanent bounded G2.10 report."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def write_report(workspace: Path) -> dict[str, object]:
    result_path = next((path for path in (workspace / "locked-results.json", workspace / "kernel-results.json", workspace / "kernel-development-results.json") if path.exists()), None)
    if result_path is None: raise RuntimeError("G2.10 has no measured result")
    result = json.loads(result_path.read_text()); metrics = result.get("metrics", {})
    lines = ["# G2.10 — Behavioral Topology Coordinate Compiler", "", f"**Classification: {result['classification']}**", "", "G2.10 predicts a registered factor's observable behavior, then projects that proposal into exact named G1 roles. Continuous coordinates never authorize topology without G1, FieldIR, provenance and numeric-field validation.", "", "## Measured scorecard", "", "| Metric | Value |", "| --- | ---: |", *[f"| {name} | {value} |" for name, value in sorted(metrics.items())], "", "## Boundary", "", "This experiment is limited to one binary factor in one of nine canonical behavioral cells. A kernel-only result measures supplied-atom topology reconstruction; only a full locked result measures raw controlled sentence compilation. It does not establish unrestricted language, multi-factor composition, identity resolution or document compilation."]
    target = ROOT / "docs" / "experiments" / "gaps" / "g02-10" / "report.md"; target.write_text("\n".join(lines) + "\n")
    return {"classification": result["classification"], "report": str(target)}
