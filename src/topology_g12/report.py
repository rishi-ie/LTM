from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def report(workspace: Path) -> dict:
    result = json.loads((workspace / "locked-results.json").read_text())
    lines = ["# G12 — Persistent Block Store and Incremental Compilation Report", "", "## Classification", "", f"**{result['classification']}**", "", "## Locked result", "", "The locked store contains one million compact topology objects in one thousand immutable memory-mapped regions. Updates use copy-on-write blocks, checksummed summaries and an atomic SQLite version pointer.", "", "| Measurement | Result |", "| --- | ---: |"]
    for key, value in result["metrics"].items():
        lines.append(f"| {key.replace('_', ' ')} | {value} |")
    lines += ["", f"Runtime: `{result['runtime_seconds']:.4f} s`; peak RSS: `{result['peak_rss_mb']:.2f} MB`.", "", "## Bounded conclusion", "", "A pass demonstrates deterministic local storage updates, source-to-object deletion lineage, immutable historical versions, atomic crash recovery and checksum rejection on the registered synthetic million-object topology. It does not demonstrate raw-language compilation, semantic quality, conversational decoding, or 100M-token reliability."]
    target = ROOT / "docs" / "experiments" / "gaps" / "g12" / "report.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n")
    return {"classification": result["classification"], "report": str(target)}
