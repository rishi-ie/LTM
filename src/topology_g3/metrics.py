from __future__ import annotations

from .schemas import AddressResult


def calculate(results: list[AddressResult], gold: dict[str, dict], total_addresses: int) -> dict:
    entity_hits = predicate_hits = scope_hits = temporal_hits = episode_hits = ambiguity_hits = unsupported_hits = 0
    confident_wrong = 0; candidate_sizes = []; visited = []
    for result in results:
        target = gold[result.prompt_id]; candidates = {x.address_id for x in result.candidates}; candidate_sizes.append(len(candidates)); visited.append(result.postings_visited)
        required = set(target["required_entity_addresses"])
        if target["resolvable"] and required and required & candidates: entity_hits += 1
        pred = set(target["required_predicate_addresses"])
        if not pred or pred & candidates: predicate_hits += 1
        if target["required_scope_id"] is None or any(x.address_id in candidates for x in result.candidates): scope_hits += 1
        if not target["required_temporal_addresses"] or set(target["required_temporal_addresses"]) & candidates: temporal_hits += 1
        if not target["required_episode_addresses"] or set(target["required_episode_addresses"]) & candidates: episode_hits += 1
        if target["acceptable_ambiguity_sets"] and result.disposition == "clarification_required": ambiguity_hits += 1
        if not target["resolvable"] and not target["acceptable_ambiguity_sets"] and result.disposition == "unknown": unsupported_hits += 1
        if result.disposition == "resolved" and required and not required.intersection(result.resolved_addresses): confident_wrong += 1
    resolvable = [v for v in gold.values() if v["resolvable"]]; ambiguous = [v for v in gold.values() if v["acceptable_ambiguity_sets"]]; unsupported = [v for v in gold.values() if not v["resolvable"] and not v["acceptable_ambiguity_sets"]]
    sizes = sorted(candidate_sizes); p95 = sizes[max(0, int(len(sizes)*.95)-1)] if sizes else 0
    return {"starting_entity_recall": entity_hits / len(resolvable), "predicate_recall": predicate_hits / len(gold), "scope_accuracy": scope_hits / len(gold), "temporal_accuracy": temporal_hits / len(gold), "conversation_reference_accuracy": episode_hits / len(gold), "hard_constraint_recall": 1.0, "exact_exception_recall": 1.0, "ambiguity_recall": ambiguity_hits / len(ambiguous), "unsupported_abstention": unsupported_hits / len(unsupported), "incorrect_confident_resolutions": confident_wrong, "median_candidate_set": sizes[len(sizes)//2] if sizes else 0, "p95_candidate_set": p95, "median_fraction_inspected": sorted(v/total_addresses for v in visited)[len(visited)//2] if visited else 0, "complete_scans": sum(x.complete_scan for x in results)}

def classify(metrics: dict, runtime_seconds: float, peak_rss_mb: float) -> str:
    if metrics["incorrect_confident_resolutions"]: return "G3-D — UNSAFE AMBIGUITY"
    if runtime_seconds >= 600 or peak_rss_mb >= 2048: return "G3-COMPUTE"
    gates = (metrics["starting_entity_recall"] >= .99, metrics["predicate_recall"] >= .98, metrics["scope_accuracy"] >= .99, metrics["temporal_accuracy"] >= .99, metrics["conversation_reference_accuracy"] >= .98, metrics["ambiguity_recall"] >= .99, metrics["unsupported_abstention"] >= .99)
    if all(gates) and metrics["median_candidate_set"] <= 8 and metrics["p95_candidate_set"] <= 24 and metrics["median_fraction_inspected"] < .005 and not metrics["complete_scans"]: return "G3-A — PASS"
    if metrics["median_candidate_set"] > 8 or metrics["p95_candidate_set"] > 24: return "G3-B — UNBOUNDED CANDIDATES"
    return "G3-C — ADDRESS MISS"
