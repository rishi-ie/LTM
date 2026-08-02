from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _gate(metrics: dict[str, Any]) -> dict[str, bool]:
    by_depth = metrics.get("by_depth", {})
    controls = metrics.get("controls", {})
    full = float(metrics.get("full_accuracy", 0.0))
    bary = float(controls.get("barycenter", 0.0))
    fact = float(controls.get("fact_only", 0.0))
    undirected = float(controls.get("undirected", 0.0))
    return {
        "full_accuracy": full >= 0.95,
        "depth_eight": float(by_depth.get("8", 0.0)) >= 0.85,
        "seed_floor": min(metrics.get("by_seed", {}).values() or [0.0]) >= 0.90,
        "barycenter_margin": full - bary >= 0.25,
        "fact_only_margin": full - fact >= 0.25,
        "undirected_margin": full - undirected >= 0.20,
        "state_swap": metrics.get("state_swap_accuracy", 0.0) >= 0.95,
        "no_energy_increases": metrics.get("energy_increases", 1) == 0,
        "no_numerical_failures": metrics.get("numerical_failures", 1) == 0,
    }


def report(workspace: Path) -> dict[str, Any]:
    results_path = workspace / "locked-results.json"
    if not results_path.exists():
        raise FileNotFoundError("run evaluate before report")
    results = json.loads(results_path.read_text())
    selected = json.loads((workspace / "selected.json").read_text())
    gates = _gate(results["metrics"])
    classification = "MICRO-LTM-A" if all(gates.values()) else "MICRO-LTM-B"
    payload = {"classification": classification, "gates": gates, "metrics": results["metrics"], "selected": selected}
    (workspace / "gate-report.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
    m = results["metrics"]
    controls = m.get("controls", {})
    lines = [
        "# MICRO-LTM-1 — Causal Latent Equilibrium Report", "",
        f"**Classification: `{classification}`**", "",
        "This compact CPU experiment tests whether a typed topology can move one fixed-size latent state through unseen multi-step relations and whether a decoder using only the final state can recover the target label.", "",
        "## Results", "",
        f"- Locked cases: {m.get('row_count', 0)} ({m.get('pair_count', 0)} counterfactual pairs)",
        f"- Full-field accuracy: **{m.get('full_accuracy', 0.0):.3f}**",
        f"- Depth-8 accuracy: **{m.get('by_depth', {}).get('8', 0.0):.3f}**",
        f"- Symbolic oracle: **{m.get('oracle_accuracy', 0.0):.3f}**",
        f"- Barycenter control: **{controls.get('barycenter', 0.0):.3f}**",
        f"- Fact-only control: **{controls.get('fact_only', 0.0):.3f}**",
        f"- Undirected-rule control: **{controls.get('undirected', 0.0):.3f}**",
        f"- State-swap causal accuracy: **{m.get('state_swap_accuracy', 0.0):.3f}**",
        "",
        "## Gate status", "",
        "| Gate | Result |", "|---|---|",
    ]
    for name, passed in gates.items():
        lines.append(f"| {name} | {'PASS' if passed else 'FAIL'} |")
    lines += [
        "", "## Interpretation", "",
        "A passing result is deliberately narrow: it would show causal latent encoding for the registered symbolic topology, not unrestricted language reasoning. A B result means the optimizer is mechanically useful but the single 128-dimensional state or decoder does not yet meet the causal gates.",
        "", "## Reproducibility", "",
        "Raw locked artifacts are kept under the ignored workspace. The selected field weights, decoder parameters, suite hashes and all per-case outputs are recorded in JSON so the run can be audited without changing the locked result.", "",
    ]
    doc = Path(__file__).resolve().parents[2] / "docs" / "micro-ltm-report.md"
    doc.write_text("\n".join(lines))
    return payload

