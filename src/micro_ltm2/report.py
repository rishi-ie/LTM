from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _gates(m: dict[str, Any]) -> dict[str, bool]:
    controls = m.get("controls", {})
    by_depth = m.get("by_depth", {})
    return {
        "compressed_accuracy": m.get("full_accuracy", 0.0) >= 0.95,
        "compressed_macro_f1": m.get("macro_f1", 0.0) >= 0.95,
        "structured_accuracy": m.get("direct_structured_accuracy", 0.0) >= 0.995,
        "depth_eight": by_depth.get("8", 0.0) >= 0.90,
        "compression_gap": m.get("direct_structured_accuracy", 0.0) - m.get("full_accuracy", 0.0) <= 0.03,
        "fact_margin": m.get("full_accuracy", 0.0) - controls.get("fact_only", 0.0) >= 0.25,
        "direction_margin": m.get("full_accuracy", 0.0) - controls.get("undirected", 0.0) >= 0.20,
        "state_swap": m.get("state_swap_accuracy", 0.0) >= 0.95,
        "rule_removal": m.get("interventions", {}).get("remove", 0.0) >= 0.95,
        "rule_reversal": m.get("interventions", {}).get("reverse", 0.0) >= 0.95,
        "interpolation": m.get("interpolation_monotonicity", 0.0) >= 0.90,
        "fixed_point": m.get("fixed_point_failures", 1) == 0,
        "no_collisions": m.get("collisions", 1) == 0,
        "runtime": m.get("runtime_seconds", 10_000.0) < 600.0,
        "memory": m.get("peak_rss_bytes", 10**12) < 1_073_741_824,
    }


def report(workspace: Path) -> dict[str, Any]:
    result_path = workspace / "locked-results.json"
    if not result_path.exists():
        raise FileNotFoundError("run evaluate before report")
    result = json.loads(result_path.read_text())
    gates = _gates(result["metrics"])
    if not gates["fixed_point"] or not gates["no_collisions"]:
        classification = "MICRO-LTM-2-F"
    elif not gates["runtime"] or not gates["memory"]:
        classification = "MICRO-LTM-2-COMPUTE"
    elif not gates["state_swap"] or not gates["rule_removal"] or not gates["rule_reversal"]:
        classification = "MICRO-LTM-2-E"
    elif not gates["depth_eight"]:
        classification = "MICRO-LTM-2-D"
    elif not gates["compressed_accuracy"] or not gates["compression_gap"]:
        classification = "MICRO-LTM-2-B"
    elif not gates["direction_margin"] or not gates["fact_margin"]:
        classification = "MICRO-LTM-2-C"
    else:
        classification = "MICRO-LTM-2-A" if all(gates.values()) else "MICRO-LTM-2-B"
    payload = {"classification": classification, "gates": gates, "metrics": result["metrics"]}
    (workspace / "gate-report.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
    m = result["metrics"]
    c = m["controls"]
    lines = [
        "# MICRO-LTM-2 — Structured Causal Relaxation Report", "",
        f"**Classification: `{classification}`**", "",
        "This experiment tests whether temporary structured field variables can reach a directed fixed point and compress that result into one latent state that is decoded without facts, rules or proofs.", "",
        "## Locked results", "",
        f"- Cases: {m['row_count']} ({m['pair_count']} counterfactual pairs)",
        f"- Compressed latent accuracy: **{m['full_accuracy']:.3f}**; macro F1: **{m['macro_f1']:.3f}**",
        f"- Direct structured accuracy: **{m['direct_structured_accuracy']:.3f}**",
        f"- Depth-8 compressed accuracy: **{m['by_depth'].get('8', 0.0):.3f}**",
        f"- Fact-only: **{c['fact_only']:.3f}**; undirected: **{c['undirected']:.3f}**; MICRO-LTM-1: **{c['old_optimizer']:.3f}**",
        f"- State swap: **{m['state_swap_accuracy']:.3f}**; interpolation: **{m['interpolation_monotonicity']:.3f}**",
        f"- Rule removal: **{m['interventions']['remove']:.3f}**; reversal: **{m['interventions']['reverse']:.3f}**",
        f"- Runtime: **{m['runtime_seconds']:.2f}s**; peak RSS: **{m['peak_rss_bytes'] / 1024 / 1024:.1f} MiB**", "",
        "## Gates", "", "| Gate | Result |", "|---|---|",
    ]
    lines.extend(f"| {name} | {'PASS' if value else 'FAIL'} |" for name, value in gates.items())
    lines += ["", "## Interpretation", "", "A passing result would establish a bounded mechanism result: a typed topology can relax locally to a directed fixed point and compress that state into a causally readable latent representation. It would not establish unrestricted language reasoning, superiority to symbolic closure, or single-vector reasoning without temporary structure.", ""]
    (Path(__file__).resolve().parents[2] / "docs" / "micro-ltm-2-report.md").write_text("\n".join(lines))
    return payload
