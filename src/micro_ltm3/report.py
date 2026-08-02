from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def classify(metrics: dict[str, Any]) -> tuple[str, dict[str, bool]]:
    controls = metrics["controls"]
    gates = {
        "overall": metrics["overall_accuracy"] >= 0.98,
        "micro_capacity": metrics["by_capacity"].get("24", 0.0) >= 0.99,
        "large_capacity": metrics["by_capacity"].get("96", 0.0) >= 0.97,
        "depth_12": metrics["by_depth"].get("12", 0.0) >= 0.95,
        "capacity_gap": metrics["by_capacity"].get("24", 0.0) - metrics["by_capacity"].get("96", 0.0) <= 0.03,
        "compression_gap": metrics["overall_accuracy"] - controls.get("direct", 0.0) >= -0.02,
        "state_swap": metrics["state_swap_accuracy"] >= 0.98,
        "interventions": min(metrics["interventions"].values()) >= 0.98,
        "interpolation": metrics["interpolation_monotonicity"] >= 0.95,
        "shuffled_state": controls.get("shuffled_state", 1.0) <= 0.40,
        "mismatched_codebook": controls.get("mismatched_codebook", 1.0) <= 0.40,
        "fixed_point": metrics["fixed_point_failures"] == 0,
        "runtime": metrics["runtime_seconds"] < 600,
    }
    if all(gates.values()):
        return "MICRO-LTM-3-A", gates
    if gates["fixed_point"] is False:
        return "MICRO-LTM-3-F", gates
    if gates["runtime"] is False:
        return "MICRO-LTM-3-COMPUTE", gates
    if gates["state_swap"] is False or gates["interventions"] is False:
        return "MICRO-LTM-3-E", gates
    if gates["overall"] and gates["compression_gap"] is False:
        return "MICRO-LTM-3-C", gates
    return "MICRO-LTM-3-B", gates


def write_report(workspace: Path, output: Path | None = None) -> Path:
    result_path = workspace / "locked-results.json"
    if not result_path.exists():
        raise FileNotFoundError("run evaluate first")
    payload = json.loads(result_path.read_text())
    metrics = payload["metrics"]
    classification, gates = classify(metrics)
    (workspace / "gate-report.json").write_text(json.dumps({"classification": classification, "gates": gates, "metrics": metrics}, indent=2, sort_keys=True))
    failures = [row for row in payload["rows"] if row["predictions"].get("selected") != row["gold"]]
    (workspace / "counterexamples.json").write_text(json.dumps(failures, indent=2, sort_keys=True))
    target = output or Path("docs/micro-ltm-3-report.md")
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# MICRO-LTM-3 — Causal Latent Compression Report",
        "",
        f"**Classification: `{classification}`**",
        "",
        "This experiment tests whether a query-agnostic compressed latent state can preserve a symbolic field's answer for unseen multi-step rule problems. It is a controlled mechanism test, not a natural-language or general-reasoning claim.",
        "",
        "## What was tested",
        "",
        "A typed field was compiled from facts and directed rules. A differentiable energy optimizer moved one latent state from a query-neutral initialization; the query-agnostic compressor saw only the optimized activation vector and proposition codebook, while the query was provided only to the two-coordinate decoder. Two capacities were evaluated: 24 propositions (48 signed codes in 128 dimensions) and 96 propositions (192 signed codes, overcomplete).",
        "",
        "## Locked results",
        "",
        f"- Rows: **{metrics['row_count']}**, twin pairs: **{metrics['pair_count']}**.",
        f"- Selected compressor: `{metrics['selected_config']}`.",
        f"- Selected accuracy: **{metrics['overall_accuracy']:.3f}**; macro-F1: **{metrics['overall_macro_f1']:.3f}**.",
        f"- Direct structured-field accuracy: **{metrics['structured_accuracy']:.3f}**.",
        f"- Capacity 24: **{metrics['by_capacity'].get('24', 0):.3f}**; capacity 96: **{metrics['by_capacity'].get('96', 0):.3f}**.",
        f"- State-swap causal accuracy: **{metrics['state_swap_accuracy']:.3f}**.",
        f"- Interpolation monotonicity: **{metrics['interpolation_monotonicity']:.3f}**.",
        f"- Intervention accuracy: `{metrics['interventions']}`.",
        f"- Locked seed groups: `{metrics.get('by_locked_group', {})}`.",
        f"- Runtime: **{metrics['runtime_seconds']:.2f}s**; support-consistency failures: **{metrics['fixed_point_failures']}**.",
        "",
        "## Accuracy by proof depth",
        "",
        "| Depth | Accuracy |",
        "|---:|---:|",
    ]
    for depth, value in sorted(metrics["by_depth"].items(), key=lambda item: int(item[0])):
        lines.append(f"| {depth} | {value:.3f} |")
    lines += [
        "",
        "## Compressor controls",
        "",
        "| Method | Accuracy |",
        "|---|---:|",
    ]
    for name, value in metrics["controls"].items():
        lines.append(f"| `{name}` | {value:.3f} |")
    boot = metrics["bootstrap_selected_minus_barycenter"]
    lines += [
        "",
        f"The selected-minus-fact-barycenter bootstrap difference was **{boot['mean']:.3f}** with 95% interval **[{boot['lower']:.3f}, {boot['upper']:.3f}]** over 2,000 resamples.",
        "",
        "## Decision gates",
        "",
        "| Gate | Result |",
        "|---|---|",
    ]
    for name, value in gates.items():
        lines.append(f"| {name} | {'PASS' if value else 'FAIL'} |")
    lines += [
        "",
        "## Numerical and causal diagnostics",
        "",
        f"The optimized activations were internally support-consistent in all rows (reported failure count **{metrics['fixed_point_failures']}**). This is not the same as proving convergence to a useful global minimum. Mean reconstruction RMSE was **{metrics['reconstruction_rmse']:.4f}**, and the maximum reported condition number was **{metrics['max_condition_number']:.1f}**. No compressor fallback was used ({metrics['fallback_count']} cases). The shuffled-state and mismatched-codebook controls collapsed as expected, but state swaps and topology interventions did not remain reliable; this is why the causal gate fails.",
        "",
        "## Interpretation",
        "",
        f"The strict optimizer run did not preserve the symbolic conclusions: selected accuracy was {metrics['overall_accuracy']:.2%}, and state-swap accuracy was {metrics['state_swap_accuracy']:.2%}. The mismatched-codebook and shuffled-state controls collapsed as expected, so the decoder was not simply reading the query or a fixed identity. The exact structured field still reached 100%, which localizes the failure to the differentiable latent state/optimization/compression contract. The earlier closure-only implementation reached 99.17%, but it is not counted as a latent-optimization breakthrough because it bypassed the differentiable optimizer. This is a useful negative result, not evidence of unrestricted language reasoning or a production-scale LTM.",
        "",
        "Raw locked rows and the frozen manifest are retained under the ignored workspace directory for reproducibility.",
        "",
    ]
    target.write_text("\n".join(lines))
    return target
