from __future__ import annotations

import json
from pathlib import Path


def report(workspace: Path) -> dict:
    results = json.loads((workspace / "locked-results.json").read_text()); metrics = results["methods"]["full"]["metrics"]
    text = "# G3 — Prompt-to-Topology Addressing Report\n\n## Classification\n\n**" + results["classification"] + "**\n\n"
    text += "G3 tested gold-validated topology plus structured prompt signatures. It does not change the failed G2/G2.1 compiler classifications.\n\n## Full resolver\n\n| Metric | Result |\n| --- | ---: |\n"
    text += "\n".join(f"| {key.replace('_', ' ')} | {value:.6g} |" for key, value in metrics.items())
    text += f"\n\nLocked runtime: `{results['runtime_seconds']:.3f} s`; peak RSS: `{results['peak_rss_mb']:.2f} MB`.\n"
    text += "\n## Controls\n\n| Method | Entity recall | Predicate recall | Median candidates |\n| --- | ---: | ---: | ---: |\n"
    for name, payload in results["methods"].items():
        row = payload["metrics"]
        text += f"| {name} | {row['starting_entity_recall']:.3f} | {row['predicate_recall']:.3f} | {row['median_candidate_set']} |\n"
    text += "\nG3-Text is supplementary. It uses the same resolver after controlled prompt-signature parsing and does not alter the G3-Core classification. G2 and G2.1 remain failed upstream compiler experiments.\n"
    out = Path(__file__).resolve().parents[2] / "docs" / "g3-addressing-report.md"; out.write_text(text); return {"report": str(out), "classification": results["classification"]}
