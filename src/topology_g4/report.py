from __future__ import annotations

import json
from pathlib import Path


def report(workspace: Path) -> dict:
    result = json.loads((workspace / "locked-results.json").read_text()); metrics = result["methods"]["full"]["metrics"]
    text = f"# G4 — Prompt-Conditioned Active Frontier Report\n\n## Classification\n\n**{result['classification']}**\n\nG4 used gold topology and gold starting addresses. It tests bounded typed traversal, not coverage certification or latent optimization.\n\n## Locked metrics\n\n| Metric | Result |\n| --- | ---: |\n"
    text += "\n".join(f"| {key.replace('_', ' ')} | {value:.6g} |" for key, value in metrics.items())
    text += f"\n\nRuntime: `{result['runtime_seconds']:.3f} s`; peak RSS: `{result['peak_rss_mb']:.2f} MB`.\n\n## Controls\n\n| Method | Required-factor recall | Conclusion agreement |\n| --- | ---: | ---: |\n"
    for name, payload in result["methods"].items(): text += f"| {name} | {payload['metrics']['required_factor_recall']:.3f} | {payload['metrics']['conclusion_agreement']:.3f} |\n"
    integration = result["g3_integration"]
    text += f"\n## G3 integration diagnostic\n\nThe actual frozen G3 resolver received controlled structured signatures and reached starting-address agreement `{integration['starting_address_agreement']:.3f}` with `{integration['unsafe_resolutions']}` unsafe resolutions. This diagnostic does not alter the G4-Core classification.\n"
    text += "\nA pass authorizes G5 only. G2/G2.1 remain failed, and G4 does not establish that unopened regions are harmless.\n"
    path = Path(__file__).resolve().parents[2] / "docs" / "g4-frontier-report.md"; path.write_text(text); return {"classification": result["classification"], "report": str(path)}
