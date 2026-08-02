from __future__ import annotations

import hashlib
import json
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np

from micro_ltm.decode import LogisticDecoder, features, train_decoder
from micro_ltm.oracle import label_for
from micro_ltm.schemas import MicroProblem, Rule, SignedLiteral

from .codebook import random_codes
from .compress import compress_equilibrium
from .decode import LABELS, decode_state
from .field import fact_mask, relax
from .generator import generate_split, save_jsonl
from .optimize import optimize_case
from .schemas import CapacityCase, CompressionConfig

CONFIGS = (
    CompressionConfig("normalized_sum"),
    CompressionConfig("raw_sum"),
    CompressionConfig("ridge", 1e-6),
    CompressionConfig("ridge", 1e-3),
    CompressionConfig("active_dual", 1e-6),
    CompressionConfig("active_dual", 1e-3),
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _accuracy(rows: list[dict[str, Any]], method: str) -> float:
    return float(np.mean([r["predictions"][method] == r["gold"] for r in rows])) if rows else 0.0


def _macro_f1(rows: list[dict[str, Any]], method: str) -> float:
    scores = []
    for label in LABELS:
        tp = sum(r["predictions"][method] == label and r["gold"] == label for r in rows)
        fp = sum(r["predictions"][method] == label and r["gold"] != label for r in rows)
        fn = sum(r["predictions"][method] != label and r["gold"] == label for r in rows)
        precision = tp / max(1, tp + fp)
        recall = tp / max(1, tp + fn)
        scores.append(2 * precision * recall / max(1e-12, precision + recall))
    return float(np.mean(scores))


def _codes(case: CapacityCase) -> np.ndarray:
    return random_codes(case)


def _legacy_state(activations: np.ndarray, codes: np.ndarray, query: int) -> np.ndarray:
    """MICRO-LTM-2-style query-anchored state, retained only as a control."""
    active = max(1.0, float(np.sum(activations)))
    raw = 0.05 * (codes[0, query] + codes[1, query])
    raw = raw + codes.reshape(-1, codes.shape[-1]).T @ activations.reshape(-1) / np.sqrt(active)
    return (raw / max(1e-12, np.linalg.norm(raw))).astype(np.float32)


def _prediction(state: np.ndarray, codes: np.ndarray, query: int, decoder: LogisticDecoder) -> str:
    return decode_state(state, codes[0, query], codes[1, query], decoder).label


def _control_states(
    full: np.ndarray,
    facts: np.ndarray,
    codes: np.ndarray,
    query: int,
    selected: CompressionConfig,
) -> dict[str, np.ndarray]:
    states: dict[str, np.ndarray] = {}
    for config in CONFIGS:
        key = config.method if config.method == "normalized_sum" else f"{config.method}_{config.ridge:g}"
        states[key] = compress_equilibrium(full, codes, config, compute_condition=False).state
    states["selected"] = compress_equilibrium(full, codes, selected, compute_condition=False).state
    states["initial"] = compress_equilibrium(facts, codes, selected, compute_condition=False).state
    states["legacy"] = _legacy_state(full, codes, query)
    states["fact_barycenter"] = compress_equilibrium(facts, codes, CompressionConfig("normalized_sum"), compute_condition=False).state
    return states


def _row(
    case: CapacityCase,
    config: CompressionConfig,
    decoder: LogisticDecoder,
    optimized: tuple[np.ndarray, list[np.ndarray], float, dict[str, float]] | None = None,
    include_controls: bool = True,
) -> dict[str, Any]:
    codes = _codes(case)
    final, trajectory, residual, optimizer_meta = optimized or optimize_case(case, codes)
    exact_final, _, _ = relax(case)
    q = case.problem.query_proposition
    facts = fact_mask(case)
    states = _control_states(final, facts, codes, q, config) if include_controls else {"selected": compress_equilibrium(final, codes, config, compute_condition=False).state, "initial": compress_equilibrium(facts, codes, config, compute_condition=False).state}
    predictions = {name: _prediction(state, codes, q, decoder) for name, state in states.items()}
    direct = "entailed" if exact_final[0, q] > 0.5 and exact_final[1, q] <= 0.5 else "contradicted" if exact_final[1, q] > 0.5 and exact_final[0, q] <= 0.5 else "unknown"
    predictions["direct"] = direct
    packed = compress_equilibrium(final, codes, config)
    trajectory_probs = []
    for activation in trajectory:
        state = compress_equilibrium(activation, codes, config, compute_condition=False).state
        trajectory_probs.append(decoder.predict(features(state, codes, q)).probabilities)
    return {
        "problem_id": case.problem.problem_id,
        "twin_id": case.problem.twin_id,
        "proposition_count": case.proposition_count,
        "density_bucket": case.density_bucket,
        "codebook_seed": case.problem.codebook_seed,
        "query": q,
        "gold": case.problem.gold_label,
        "depth": case.problem.proof_depth,
        "predictions": predictions,
        "state": packed.state.tolist(),
        "active_count": packed.active_count,
        "condition_number": packed.condition_number,
        "reconstruction_rmse": packed.reconstruction_rmse,
        "fixed_residual": residual,
        "trajectory": [list(map(float, probs)) for probs in trajectory_probs],
        "state_norm": packed.state_norm,
        "fallback_used": packed.fallback_used,
        "optimizer": optimizer_meta,
    }


def _training_features(
    cases: list[CapacityCase],
    config: CompressionConfig,
    optimized: dict[str, tuple[np.ndarray, list[np.ndarray], float, dict[str, float]]] | None = None,
) -> tuple[np.ndarray, list[str]]:
    x = []
    labels = []
    for case in cases:
        codes = _codes(case)
        final = (optimized[case.problem.problem_id][0] if optimized is not None else optimize_case(case, codes)[0])
        state = compress_equilibrium(final, codes, config).state
        q = case.problem.query_proposition
        x.append(features(state, codes, q))
        labels.append(case.problem.gold_label)
    return np.asarray(x), labels


def develop(workspace: Path) -> dict[str, Any]:
    if (workspace / "selected.json").exists():
        raise FileExistsError("development already exists")
    workspace.mkdir(parents=True, exist_ok=True)
    train = generate_split("train3-micro", 1200, 3729, 24, range(1, 5), False)
    train += generate_split("train3-large", 1200, 3730, 96, range(1, 5), False)
    dev = generate_split("dev3-micro", 300, 3731, 24, range(1, 9), True)
    dev += generate_split("dev3-large", 300, 3732, 96, range(1, 9), True)
    save_jsonl(workspace / "train.jsonl", train)
    save_jsonl(workspace / "dev.jsonl", dev)
    train_optimized = {case.problem.problem_id: optimize_case(case, _codes(case)) for case in train}
    dev_optimized = {case.problem.problem_id: optimize_case(case, _codes(case)) for case in dev}
    best: tuple[float, float, float, float] = (-1.0, -1.0, -1.0, -1.0)
    selected: dict[str, Any] | None = None
    for config in CONFIGS:
        x, labels = _training_features(train, config, train_optimized)
        for lr in (0.01, 0.05):
            for l2 in (0.0, 0.001):
                decoder = train_decoder(x, labels, lr, l2)
                rows = [_row(case, config, decoder, dev_optimized[case.problem.problem_id], include_controls=False) for case in dev]
                large = [r for r in rows if r["proposition_count"] == 96]
                score = (_macro_f1(large, "selected"), _accuracy(large, "selected"), _accuracy(rows, "selected"), -float(np.mean([r["fixed_residual"] for r in rows])))
                if score > best:
                    best = score
                    selected = {"config": {"method": config.method, "ridge": config.ridge}, "decoder_weights": decoder.weights.tolist(), "decoder_bias": decoder.bias.tolist(), "development_score": score, "learning_rate": lr, "l2": l2}
    assert selected is not None
    (workspace / "selected.json").write_text(json.dumps(selected, indent=2, sort_keys=True))
    return {"selected": selected, "train_count": len(train), "dev_count": len(dev)}


def freeze(workspace: Path) -> dict[str, Any]:
    if (workspace / "frozen-manifest.json").exists():
        raise FileExistsError("workspace is already frozen")
    required = [workspace / "selected.json", workspace / "train.jsonl", workspace / "dev.jsonl"]
    if not all(p.exists() for p in required):
        raise FileNotFoundError("run develop first")
    manifest = {"experiment": "MICRO-LTM-3", "selected_sha256": _sha(required[0]), "train_sha256": _sha(required[1]), "dev_sha256": _sha(required[2]), "locked_seeds": [20261021, 20261022, 20261023, 20261024, 20261025, 20261026]}
    (workspace / "frozen-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return manifest


def _interventions(cases: list[CapacityCase], config: CompressionConfig, decoder: LogisticDecoder) -> dict[str, float]:
    outcomes: dict[str, list[bool]] = {"remove": [], "reverse": [], "add": []}
    for case in cases:
        p = case.problem
        if p.twin_id is not None:
            continue
        variants: list[tuple[str, MicroProblem]] = []
        if p.gold_label == "unknown":
            variants.append(("add", replace(p, rules=p.rules + (Rule("intervention-add", (p.facts[0],), SignedLiteral(p.query_proposition, -1)),))))
        elif p.decisive_rule_id:
            variants.append(("remove", replace(p, rules=tuple(r for r in p.rules if r.rule_id != p.decisive_rule_id))))
            reversed_rules = tuple(Rule(r.rule_id, r.premises, SignedLiteral(r.conclusion.proposition, -r.conclusion.polarity)) if r.rule_id == p.decisive_rule_id else r for r in p.rules)
            variants.append(("reverse", replace(p, rules=reversed_rules)))
        for name, altered in variants:
            altered_case = CapacityCase(altered, case.proposition_count, case.density_bucket)
            codes = _codes(altered_case)
            final, _, _, _ = optimize_case(altered_case, codes)
            state = compress_equilibrium(final, codes, config).state
            pred = _prediction(state, codes, altered.query_proposition, decoder)
            outcomes[name].append(pred == label_for(altered))
    return {key: float(np.mean(value)) if value else 0.0 for key, value in outcomes.items()}


def _bootstrap_delta(rows: list[dict[str, Any]], a: str, b: str, seed: int = 93729, samples: int = 2000) -> tuple[float, float, float]:
    rng = np.random.default_rng(seed)
    deltas = []
    n = len(rows)
    for _ in range(samples):
        picked = [rows[int(i)] for i in rng.integers(0, n, size=n)]
        deltas.append(_accuracy(picked, a) - _accuracy(picked, b))
    return float(np.mean(deltas)), float(np.quantile(deltas, 0.025)), float(np.quantile(deltas, 0.975))


def evaluate_locked(workspace: Path) -> dict[str, Any]:
    if not (workspace / "frozen-manifest.json").exists():
        raise FileNotFoundError("run freeze first")
    if (workspace / "locked-results.json").exists():
        raise FileExistsError("locked evaluation already exists")
    selected = json.loads((workspace / "selected.json").read_text())
    config = CompressionConfig(**selected["config"])
    decoder = LogisticDecoder(np.asarray(selected["decoder_weights"]), np.asarray(selected["decoder_bias"]))
    cases: list[CapacityCase] = []
    for seed in (20261021, 20261022, 20261023):
        cases += generate_split(f"locked-{seed}", 300, seed, 24, range(6, 13), True)
    for seed in (20261024, 20261025, 20261026):
        cases += generate_split(f"locked-{seed}", 300, seed, 96, range(6, 13), True)
    save_jsonl(workspace / "locked.jsonl", cases)
    start = time.perf_counter()
    optimized = {case.problem.problem_id: optimize_case(case, _codes(case)) for case in cases}
    rows = [_row(case, config, decoder, optimized[case.problem.problem_id]) for case in cases]
    by_id = {r["problem_id"]: r for r in rows}
    case_by_id = {c.problem.problem_id: c for c in cases}
    pairs = [(by_id[p.problem.problem_id], by_id[p.problem.twin_id]) for p in cases if p.problem.twin_id and p.problem.twin_id in by_id]
    swaps: list[bool] = []
    interpolations: list[bool] = []
    for source, destination in pairs:
        case = case_by_id[source["problem_id"]]
        codes = _codes(case)
        qa = case.problem.query_proposition
        p_source = _prediction(np.asarray(destination["state"], dtype=np.float32), codes, qa, decoder)
        p_destination = _prediction(np.asarray(source["state"], dtype=np.float32), codes, qa, decoder)
        swaps.append(p_source == destination["gold"] and p_destination == source["gold"])
        for a, b in ((source, destination), (destination, source)):
            values = []
            for alpha in (0.0, 0.25, 0.5, 0.75, 1.0):
                state = (1 - alpha) * np.asarray(a["state"]) + alpha * np.asarray(b["state"])
                values.append(decoder.predict(features(state, codes, qa)).probabilities[LABELS.index(b["gold"])])
            interpolations.append(all(values[i + 1] + 1e-3 >= values[i] for i in range(4)))
    method_names = ["selected", "normalized_sum", "raw_sum", "ridge_1e-06", "ridge_0.001", "active_dual_1e-06", "active_dual_0.001", "initial", "legacy", "fact_barycenter", "direct"]
    controls = {method: _accuracy(rows, method) for method in method_names if method in rows[0]["predictions"]}
    # Anti-shortcut controls use the same decoder but break the state/codebook
    # association.  They are evaluated only after the locked states exist.
    shuffled_predictions: list[bool] = []
    mismatch_predictions: list[bool] = []
    by_capacity_rows = {size: [r for r in rows if r["proposition_count"] == size] for size in (24, 96)}
    for capacity_rows in by_capacity_rows.values():
        for index, row in enumerate(capacity_rows):
            own_case = case_by_id[row["problem_id"]]
            other = capacity_rows[(index + 1) % len(capacity_rows)]
            own_codes = _codes(own_case)
            query = row["query"]
            shuffled_predictions.append(_prediction(np.asarray(other["state"], dtype=np.float32), own_codes, query, decoder) == row["gold"])
            mismatch_case = case_by_id[capacity_rows[(index + 17) % len(capacity_rows)]["problem_id"]]
            mismatch_codes = _codes(mismatch_case)
            mismatch_predictions.append(_prediction(np.asarray(row["state"], dtype=np.float32), mismatch_codes, query, decoder) == row["gold"])
    controls["shuffled_state"] = float(np.mean(shuffled_predictions))
    controls["mismatched_codebook"] = float(np.mean(mismatch_predictions))
    selected_pairs = _bootstrap_delta(rows, "selected", "fact_barycenter")
    by_group = {}
    for group in sorted({"-".join(r["problem_id"].split("-")[:2]) for r in rows}):
        by_group[group] = _accuracy([r for r in rows if "-".join(r["problem_id"].split("-")[:2]) == group], "selected")
    max_trajectory = max(len(r["trajectory"]) for r in rows)
    trajectory_mean = [
        float(np.mean([r["trajectory"][index][LABELS.index(r["gold"])] for r in rows if index < len(r["trajectory"])]))
        for index in range(max_trajectory)
    ]
    metrics = {
        "selected_config": selected["config"],
        "overall_accuracy": _accuracy(rows, "selected"),
        "overall_macro_f1": _macro_f1(rows, "selected"),
        "structured_accuracy": _accuracy(rows, "direct"),
        "by_capacity": {str(size): _accuracy([r for r in rows if r["proposition_count"] == size], "selected") for size in (24, 96)},
        "by_depth": {str(depth): _accuracy([r for r in rows if r["depth"] == depth], "selected") for depth in sorted({r["depth"] for r in rows})},
        "by_locked_group": by_group,
        "trajectory_correct_probability": trajectory_mean,
        "controls": controls,
        "bootstrap_selected_minus_barycenter": {"mean": selected_pairs[0], "lower": selected_pairs[1], "upper": selected_pairs[2], "samples": 2000},
        "state_swap_accuracy": float(np.mean(swaps)),
        "interpolation_monotonicity": float(np.mean(interpolations)),
        "interventions": _interventions(cases, config, decoder),
        "fixed_point_failures": int(sum(r["fixed_residual"] > 1e-7 for r in rows)),
        "reconstruction_rmse": float(np.mean([r["reconstruction_rmse"] for r in rows])),
        "max_condition_number": float(max(r["condition_number"] for r in rows)),
        "runtime_seconds": time.perf_counter() - start,
        "row_count": len(rows),
        "pair_count": len(pairs),
        "fallback_count": int(sum(r["fallback_used"] for r in rows)),
    }
    result = {"experiment": "MICRO-LTM-3", "metrics": metrics, "rows": rows}
    (workspace / "locked-results.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    return result
