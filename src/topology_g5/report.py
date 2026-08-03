from __future__ import annotations

import json
from pathlib import Path


def report(workspace: Path) -> dict:
    result = json.loads((workspace / "locked-results.json").read_text()); metrics = result["methods"]["full"]["metrics"]
    text = "# G5 — Certified Coverage, Distant Influence, and Automatic Widening\n\n"
    text += f"## Classification\n\n**{result['classification']}**\n\n"
    text += "G5 uses gold topology and starting addresses. It tests deterministic summaries and an additive quadratic field, not arbitrary nonlinear latent optimization or language ingestion.\n\n"
    text += "## Locked metrics\n\n| Metric | Result |\n| --- | ---: |\n"
    text += "\n".join(f"| {key.replace('_', ' ')} | {value:.6g} |" for key, value in metrics.items())
    text += f"\n\nRuntime: `{result['runtime_seconds']:.3f} s`; peak RSS: `{result['peak_rss_mb']:.2f} MB`; summaries: `{result['summary_count']}`.\n\n"
    text += "## Controls\n\n| Method | Conclusion agreement | False certified |\n| --- | ---: | ---: |\n"
    for name, payload in result["methods"].items():
        values = payload["metrics"]; text += f"| {name} | {values['final_conclusion_agreement']:.3f} | {values['false_certified']:.0f} |\n"
    text += "\nA passing result authorizes G6 only in this controlled field law. G2/G2.1 remain unresolved, and this result does not establish arbitrary-field coverage or 100-million-token reliability.\n"
    path = Path(__file__).resolve().parents[2] / "docs" / "g5-coverage-report.md"; path.write_text(text); return {"classification": result["classification"], "report": str(path)}
