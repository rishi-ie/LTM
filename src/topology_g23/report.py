from __future__ import annotations

import json
from pathlib import Path


def report(workspace: Path) -> dict[str, object]:
    result = json.loads((workspace / "locked-results.json").read_text())
    path = workspace / "g2-3-compiler-report.md"
    lines = ["# G2.3 — Hierarchical Sentence-to-Topology Compiler Report", "", f"Classification: **{result['classification']}**", "", "This result is bounded to controlled unseen language in the frozen G1 ontology.", "", "## Runtime", "", f"- operational candidate: `{result['operational']}`", f"- runtime seconds: `{result['runtime_seconds']:.3f}`", f"- peak RSS MB: `{result['peak_rss_mb']:.1f}`", "", "## Methods", ""]
    for name, values in result["methods"].items():
        lines.extend([f"### {name}", "", "```json", json.dumps(values, indent=2, sort_keys=True), "```", ""])
    lines.extend(["## Boundary", "", "This does not establish unrestricted-language ingestion, latent optimization, decoder quality or 100M-context reliability. G2, G2.1 and G2.2 remain immutable historical results."])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"report": str(path), "classification": result["classification"]}
