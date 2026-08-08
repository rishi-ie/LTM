from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def report(workspace: Path) -> dict:
    result = json.loads((workspace / "locked-results.json").read_text())
    metrics = result["metrics"]
    lines = ["# G11 — Safe Conversation-Memory Lifecycle Report", "", "## Classification", "", f"**{result['classification']}**", "", "## Locked result", "", "G11 ran 32 deterministic twelve-turn conversations against an independent full-history oracle. The candidate uses an immutable base SQLite database plus a copy-on-write session overlay.", "", "| Measurement | Result |", "| --- | ---: |"]
    for key, value in metrics.items():
        if isinstance(value, (dict, list)):
            continue
        lines.append(f"| {key.replace('_', ' ')} | {value} |")
    lines += ["", f"Runtime: `{result['runtime_seconds']:.4f} s`; peak RSS: `{result['peak_rss_mb']:.2f} MB`.", "", "## Bounded conclusion", "", "A pass establishes only the controlled lifecycle contract: session context, corrections, preferences, scoped conflicts, episode summaries, restarts, deletion and clearing preserve the registered state and provenance without mutating base knowledge. Assistant text remains a low-authority discourse event, not independent evidence. This does not establish natural-language compilation, model decoding, integrated conversation quality, or 100M-context reliability."]
    target = ROOT / "docs" / "experiments" / "gaps" / "g11" / "report.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n")
    return {"classification": result["classification"], "report": str(target)}
