"""Measured I3 report writer."""

from __future__ import annotations

import json
from pathlib import Path


def write_report(workspace: Path) -> Path:
    development = json.loads((workspace / "development-results.json").read_text(encoding="utf-8")) if (workspace / "development-results.json").exists() else None
    locked = json.loads((workspace / "locked-results.json").read_text(encoding="utf-8")) if (workspace / "locked-results.json").exists() else None
    lines = ["# I3 — Latent-Guided Formal Mathematical Hopping", "", "## Measured status", ""]
    if locked is None:
        lines += ["No locked result is authorized or available.", "", "Development evidence:", "", "```json", json.dumps(development or {}, indent=2, sort_keys=True), "```"]
    else:
        lines += ["```json", json.dumps(locked, indent=2, sort_keys=True), "```"]
    target = workspace / "report.md"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target
