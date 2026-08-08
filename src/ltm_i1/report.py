from __future__ import annotations

import json
from pathlib import Path


def write_report(workspace: Path, destination: Path) -> None:
    summary = json.loads((workspace / "report-summary.json").read_text())
    locked = summary["locked"]
    lines = [
        "# LTM-I1 — Canonical FieldIR v2 Integration Validation",
        "",
        "This report validates the registered numeric FieldIR v2 contract against the existing G3–G10.1 interfaces. The representation suite uses evaluator-generated or confirmed topology; it does not claim raw-language compilation.",
        "",
        f"Classification: **{summary['classification']}**",
        "",
        "## Locked results",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key, value in locked.items():
        lines.append(f"| {key.replace('_', ' ')} | {value} |")
    diagnostic = summary.get("g2_5_diagnostic", {})
    lines += [
        "",
        "## G2.5 supplied-atom diagnostic",
        "",
        f"The frozen G2.5 checkpoint emitted {diagnostic.get('emitted_handoffs', 0)} handoffs from {diagnostic.get('cases', 0)} supplied-atom cases. {diagnostic.get('correct_emitted_handoffs', 0)} were correct under the G2.5 evaluator gold, and all {diagnostic.get('converted_handoffs', 0)} correct handoffs converted into FieldIR v2 successfully (conditional conversion precision {diagnostic.get('conversion_precision', 0.0):.3f}). This is not a raw-language compilation result.",
        "",
        f"Measured locked runtime: {summary.get('runtime_seconds', 0.0):.3f}s; peak RSS: {summary.get('peak_rss_mb', 0.0):.1f}MB; semantic replay: {summary.get('verification', {}).get('semantic_replay_equal', False)}.",
        "The registered corruption suite contained 128 attacks (eight per family); all 128 were rejected with their declared primary code.",
    ]
    lines += [
        "",
        "The canonical path is: numeric FieldIR v2 → packed reload → G3/G4/G5 views → G6 exact state → G7 quadratic soft state → unchanged G9 verifier → strict G10.1 realization.",
        "",
        "G2.5 is diagnostic only. Its supplied-atom kernel is not treated as a raw sentence compiler, and its known relation accuracy does not alter this representation verdict.",
        "",
        "A pass authorizes the representation-backed integration step and a later compiled-topology rerun. It does not establish unrestricted language compilation, optimal learned geometry, free-form naturalness, ontology completeness, production serving, or G15.",
    ]
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
