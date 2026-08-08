"""Permanent bounded report for the G2.5 representation-kernel decision."""

from __future__ import annotations

import json
from pathlib import Path


def write_report(workspace: Path, destination: Path) -> None:
    result = json.loads((workspace / "kernel-results.json").read_text(encoding="utf-8"))
    metrics = result["metrics"]
    lines = [
        "# G2.5 — Typed Atom Coordinate Compiler and Latent-Field Handoff",
        "",
        "## Kernel decision",
        "",
        f"**{result['classification']}**",
        "",
        "This is the locked, gold-atom representation-kernel decision. It measures operator, role and context decoding before complete span extraction or persistent-identity composition.",
        "",
        "## Locked measurements",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {key.replace('_', ' ')} | {value} |" for key, value in metrics.items())
    lines += [
        "",
        "## Boundary",
        "",
        "A kernel failure stops G2.5 by design: it rejects this typed-coordinate representation before additional compiler training is spent. A kernel pass is necessary but not sufficient for a controlled G2 pass; sentence extraction, identity, document composition and field handoff then remain to be evaluated on a separately frozen suite.",
        "",
    ]
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines), encoding="utf-8")
