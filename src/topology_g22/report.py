"""Tracked bounded report; raw predictions stay in the ignored workspace."""
from __future__ import annotations

import json
from pathlib import Path

from .io import write_json

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "docs" / "roadmap" / "results-ledger.md"
REPORT = ROOT / "docs" / "experiments" / "gaps" / "g02-2" / "report.md"


def _update_ledger(results: dict[str, object]) -> None:
    """Append the completed result once; historical result text is never rewritten."""
    ledger = LEDGER.read_text(encoding="utf-8")
    if "## 20. G2.2 — Sentence-level reasoning compiler" in ledger:
        return
    status = "**PASS**" if str(results["classification"]).startswith("G2.2-O-PASS") else "**FAILED**"
    line = f"| G2.2 | Sentence-level reasoning compiler | {status} | `{results['classification']}` | See G2.2 report; historical G2/G2.1 remain unchanged |"
    marker = "| G3 | Prompt-to-topology addressing"
    if marker in ledger:
        ledger = ledger.replace(marker, line + "\n" + marker, 1)
    sentence = results["methods"][results["operational"]]["sentence"]
    links = results["methods"][results["operational"]]["link"]
    appendix = [
        "",
        "## 20. G2.2 — Sentence-level reasoning compiler",
        "",
        "- Experiment: [G2.2 specification](../experiments/gaps/g02-2/specification.md)",
        "- Authoritative report: [G2.2 locked report](../experiments/gaps/g02-2/report.md)",
        f"- Mechanical classification: **`{results['classification']}`**",
        f"- Accepted sentence exact precision / safe coverage: `{sentence['accepted_exact_precision']:.4f}` / `{sentence['safe_coverage']:.4f}`.",
        f"- Link exact precision / safe coverage: `{links['link_exact_precision']:.4f}` / `{links['link_safe_coverage']:.4f}`.",
        f"- Locked runtime / peak RSS: `{results['runtime_seconds']:.3f} s` / `{results['peak_rss_mb']:.1f} MB`.",
        "",
        "This is a controlled G1-ontology compiler result only. It does not revise the historical G2 or G2.1 result or establish raw-language product readiness.",
        "",
    ]
    LEDGER.write_text(ledger.rstrip() + "\n" + "\n".join(appendix), encoding="utf-8")


def report(workspace: Path) -> dict[str, object]:
    results_path = workspace / "locked-results.json"
    if not results_path.exists():
        raise RuntimeError("locked evaluation is required before reporting")
    results = json.loads(results_path.read_text())
    lines = [
        "# G2.2 — Sentence-Level Reasoning Compiler Report",
        "",
        "## Status",
        "",
        f"**{results['classification']}**",
        "",
        "This result is bounded to controlled unseen language in the G1 ontology. It does not establish",
        "unrestricted language ingestion, latent optimization, decoder quality, or 100M-context reliability.",
        "",
        "## Locked measurements",
        "",
        f"- Operational candidate: `{results['operational']}`",
        f"- Runtime: {results['runtime_seconds']:.3f} seconds",
        f"- Peak RSS: {results['peak_rss_mb']:.1f} MB",
        f"- Network calls: {results['network_calls']}",
        "",
        "## Gates",
        "",
    ]
    lines.extend(f"- `{name}`: {'pass' if value else 'fail'}" for name, value in results["gates"].items())
    lines.extend(("", "## Method metrics", ""))
    for name, metrics in results["methods"].items():
        lines.append(f"### {name}")
        lines.append("")
        lines.append(f"- Sentence: `{json.dumps(metrics['sentence'], sort_keys=True)}`")
        lines.append(f"- Link: `{json.dumps(metrics['link'], sort_keys=True)}`")
        lines.append("")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    workspace_report = workspace / "g2-2-reasoning-compiler-report.md"
    workspace_report.write_text(REPORT.read_text(), encoding="utf-8")
    write_json(workspace / "gate-report.json", {"classification": results["classification"], "gates": results["gates"]})
    _update_ledger(results)
    return {"report": str(REPORT), "classification": results["classification"]}
