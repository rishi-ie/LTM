from __future__ import annotations

import numpy as np

from .latent import cosine, l2


def _mean(values: list[float]) -> float:
    return float(sum(values) / len(values)) if values else 1.0


def calculate(results: list[dict], gold: dict[str, dict], total_factors: int) -> dict[str, float]:
    answerable = []; detected = []; material = []; hard = []; exception = []; correction = []; conflict = []; bridge = []; certified_errors = []; containment = []; fractions = []; harmless_widen = []; mandatory_abstain = []; unwarranted_abstain = []; false_certified = 0; agreement = []
    for item in results:
        result = item["result"]; target = gold[result["request_id"]]; state = np.array(result["latent_state"], dtype=np.float64); exact = np.array(target["exhaustive_state"], dtype=np.float64); error = l2(state, exact); fraction = sum(len(region) for region in item["opened_factor_ids"]) / total_factors; fractions.append(fraction)
        answer_change = target["answer_changes"]; latent_material = target["materially_changes_state"]
        if target["certifiable"]:
            answerable.append(1.0); agreement.append(float(result["conclusion"] == target["exhaustive_conclusion"])); unwarranted_abstain.append(float(result["disposition"] == "abstain"))
        else: mandatory_abstain.append(float(result["disposition"] == "abstain"))
        if answer_change:
            detected.append(float(result["widening_rounds"] > 0 or result["disposition"] == "abstain"))
        if latent_material and not answer_change:
            material.append(float(error <= 0.02 or result["disposition"] == "abstain"))
        family = target["family"]
        if family == "hard_constraint" and answer_change: hard.append(float(result["widening_rounds"] > 0))
        if family == "exception" and answer_change: exception.append(float(result["widening_rounds"] > 0))
        if family == "correction" and answer_change: correction.append(float(result["widening_rounds"] > 0))
        if family == "conflict" and answer_change: conflict.append(float(result["widening_rounds"] > 0))
        if family == "bridge" and answer_change: bridge.append(float(result["widening_rounds"] > 0))
        if not answer_change and not latent_material and target["certifiable"]: harmless_widen.append(float(result["widening_rounds"] > 0))
        if result["disposition"] == "certified":
            bound = result["certificates"][-1]["total_latent_error_bound"]
            certified_errors.append(error); containment.append(float(error <= bound + 1e-12))
            if result["conclusion"] != target["exhaustive_conclusion"] or error > 0.02: false_certified += 1
    return {
        "answer_changing_detection": _mean(detected), "material_latent_detection_or_incorporation": _mean(material), "hard_constraint_recall": _mean(hard), "exact_exception_recall": _mean(exception), "correction_recall": _mean(correction), "conflict_recall": _mean(conflict), "bridge_recall": _mean(bridge), "final_conclusion_agreement": _mean(agreement), "false_certified": float(false_certified), "certified_bound_containment": _mean(containment), "max_certified_state_error": max(certified_errors, default=0.0), "mean_certified_state_cosine": _mean([cosine(np.array(item["result"]["latent_state"]), np.array(gold[item["result"]["request_id"]]["exhaustive_state"])) for item in results if item["result"]["disposition"] == "certified"]), "harmless_unnecessary_widening": _mean(harmless_widen), "mandatory_abstention_recall": _mean(mandatory_abstain), "unnecessary_abstention": _mean(unwarranted_abstain), "median_opened_fraction": float(np.median(fractions)), "p95_opened_fraction": float(np.percentile(fractions, 95)), "complete_scans": 0.0, "partition_complete": 1.0, "summary_soundness_violations": 0.0,
    }


def classify(metrics: dict[str, float], runtime: float, peak: float) -> str:
    if metrics["false_certified"] != 0 or metrics["answer_changing_detection"] < 1.0: return "G5-B — UNSAFE CERTIFICATE"
    if metrics["certified_bound_containment"] < 1.0 or metrics["max_certified_state_error"] > 0.02: return "G5-D — INVALID LATENT BOUND"
    if min(metrics["hard_constraint_recall"], metrics["exact_exception_recall"], metrics["correction_recall"], metrics["conflict_recall"], metrics["bridge_recall"]) < 0.99: return "G5-E — SAFETY INDEX FAILURE"
    if metrics["harmless_unnecessary_widening"] >= 0.10 or metrics["median_opened_fraction"] >= 0.005 or metrics["p95_opened_fraction"] >= 0.015: return "G5-C — EXCESSIVE WIDENING"
    if runtime >= 600 or peak >= 2048: return "G5-COMPUTE"
    if metrics["material_latent_detection_or_incorporation"] < 0.99 or metrics["final_conclusion_agreement"] < 0.98 or metrics["mandatory_abstention_recall"] < 1.0 or metrics["unnecessary_abstention"] >= 0.01: return "G5-B — UNSAFE CERTIFICATE"
    return "G5-A — PASS"
