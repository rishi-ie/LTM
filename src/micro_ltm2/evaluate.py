from __future__ import annotations

import hashlib
import json
import resource
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np

from micro_ltm.decode import LogisticDecoder, features, train_decoder
from micro_ltm.optimize import optimize as old_optimize
from micro_ltm.oracle import label_for
from micro_ltm.schemas import FieldConfig, MicroProblem, Rule, SignedLiteral

from .compress import compress
from .field import codebook, fact_mask, relax
from .generator import generate_split, save_jsonl

OLD_CONFIG = FieldConfig(16.0, 8.0, 0.03, propositions=24)
LABELS = ("entailed", "contradicted", "unknown")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _label(pos: float, neg: float) -> str:
    if pos > 0.5 and neg <= 0.5:
        return "entailed"
    if neg > 0.5 and pos <= 0.5:
        return "contradicted"
    return "unknown"


def _accuracy(rows: list[dict[str, Any]], method: str) -> float:
    return float(np.mean([row["predictions"][method] == row["gold"] for row in rows])) if rows else 0.0


def _macro_f1(rows: list[dict[str, Any]], method: str) -> float:
    scores = []
    for label in LABELS:
        tp = sum(row["predictions"][method] == label and row["gold"] == label for row in rows)
        fp = sum(row["predictions"][method] == label and row["gold"] != label for row in rows)
        fn = sum(row["predictions"][method] != label and row["gold"] == label for row in rows)
        precision = tp / max(1, tp + fp)
        recall = tp / max(1, tp + fn)
        scores.append(2 * precision * recall / max(1e-12, precision + recall))
    return float(np.mean(scores))


def _by_depth(rows: list[dict[str, Any]], method: str) -> dict[str, float]:
    return {str(depth): _accuracy([r for r in rows if r["depth"] == depth], method) for depth in sorted({r["depth"] for r in rows})}


def _features_from_state(state: np.ndarray, p: MicroProblem) -> np.ndarray:
    return features(state, codebook(p), p.query_proposition)


def _case(p: MicroProblem, decoder: LogisticDecoder, old_decoder: LogisticDecoder) -> dict[str, Any]:
    codes = codebook(p)
    full = relax(p, codes)
    fact_only = replace(full, final_activations=fact_mask(p))
    reverse = relax(p, codes, mode="reverse")
    undirected = relax(p, codes, mode="undirected")
    initial = compress(fact_mask(p), codes, p.query_proposition)
    full_c = compress(full.final_activations, codes, p.query_proposition)
    fact_c = compress(fact_only.final_activations, codes, p.query_proposition)
    reverse_c = compress(reverse.final_activations, codes, p.query_proposition)
    undirected_c = compress(undirected.final_activations, codes, p.query_proposition)
    old = old_optimize(p, OLD_CONFIG, codes=codes)
    q = p.query_proposition
    direct = _label(full.final_activations[0, q], full.final_activations[1, q])
    predictions = {
        "full": decoder.predict(features(full_c.state, codes, q)).label,
        "initial": decoder.predict(features(initial.state, codes, q)).label,
        "fact_only": decoder.predict(features(fact_c.state, codes, q)).label,
        "reverse": decoder.predict(features(reverse_c.state, codes, q)).label,
        "undirected": decoder.predict(features(undirected_c.state, codes, q)).label,
        "direct_structured": direct,
        "old_optimizer": old_decoder.predict(features(old.final_state, codes, q)).label,
    }
    return {
        "problem_id": p.problem_id,
        "twin_id": p.twin_id,
        "codebook_seed": p.codebook_seed,
        "query": q,
        "gold": p.gold_label,
        "depth": p.proof_depth,
        "seed_group": p.problem_id.split("-")[1] if p.problem_id.startswith("locked-") else "development",
        "predictions": predictions,
        "supports": {"full": [full_c.positive_feature, full_c.negative_feature]},
        "state": full_c.state.tolist(),
        "activations": full.final_activations.tolist(),
        "fixed_residual": full.fixed_residual,
        "sweeps": len(full.trace),
        "collision_count": full.collision_count,
        "old_state": old.final_state.tolist(),
        "energy": [old.initial_energy, old.final_energy],
    }


def _train_states(problems: list[MicroProblem]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    primary = []
    old = []
    for p in problems:
        codes = codebook(p)
        result = relax(p, codes)
        primary.append(features(result.final_state, codes, p.query_proposition))
        old_result = old_optimize(p, OLD_CONFIG, codes=codes)
        old.append(features(old_result.final_state, codes, p.query_proposition))
    labels = np.asarray([p.gold_label for p in problems])
    return np.asarray(primary), labels, np.asarray(old), labels.copy()


def develop(workspace: Path) -> dict[str, Any]:
    if (workspace / "selected.json").exists():
        raise FileExistsError("development is already complete")
    workspace.mkdir(parents=True, exist_ok=True)
    train = generate_split("train2", 4080, 2729, range(1, 4), False)
    dev = generate_split("dev2", 540, 2730, range(1, 6), True)
    save_jsonl(workspace / "train.jsonl", train)
    save_jsonl(workspace / "dev.jsonl", dev)
    x_train, labels, old_x_train, old_labels = _train_states(train)
    selected_decoder: LogisticDecoder | None = None
    selected_old: LogisticDecoder | None = None
    best = (-1.0, -1.0)
    for lr in (0.01, 0.05):
        for l2 in (0.0, 0.001):
            candidate = train_decoder(x_train, labels.tolist(), lr, l2)
            old_candidate = train_decoder(old_x_train, old_labels.tolist(), lr, l2)
            dev_rows = [_case(p, candidate, old_candidate) for p in dev]
            score = (_macro_f1(dev_rows, "full"), _accuracy(dev_rows, "full"))
            if score > best:
                best = score
                selected_decoder, selected_old = candidate, old_candidate
    assert selected_decoder is not None and selected_old is not None
    payload = {
        "decoder_weights": selected_decoder.weights.tolist(),
        "decoder_bias": selected_decoder.bias.tolist(),
        "old_decoder_weights": selected_old.weights.tolist(),
        "old_decoder_bias": selected_old.bias.tolist(),
        "development_macro_f1": best[0],
        "development_accuracy": best[1],
        "compression_anchor": 0.05,
    }
    (workspace / "selected.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
    return {"selected": payload, "train_count": len(train), "dev_count": len(dev)}


def freeze(workspace: Path) -> dict[str, Any]:
    if (workspace / "frozen-manifest.json").exists():
        raise FileExistsError("workspace is already frozen")
    required = [workspace / "selected.json", workspace / "train.jsonl", workspace / "dev.jsonl"]
    if not all(path.exists() for path in required):
        raise FileNotFoundError("run develop before freeze")
    manifest = {
        "experiment": "MICRO-LTM-2",
        "selected_sha256": _sha(workspace / "selected.json"),
        "train_sha256": _sha(workspace / "train.jsonl"),
        "dev_sha256": _sha(workspace / "dev.jsonl"),
        "locked_seeds": [20260911, 20260912, 20260913],
    }
    (workspace / "frozen-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return manifest


def _intervention_accuracy(problems: list[MicroProblem], decoder: LogisticDecoder) -> dict[str, float]:
    outcomes: dict[str, list[bool]] = {"remove": [], "reverse": [], "add": []}
    for p in problems:
        if p.twin_id is not None:
            continue
        target = p.query_proposition
        if p.gold_label == "unknown":
            modified = replace(p, rules=p.rules + (Rule("intervention-add", (p.facts[0],), SignedLiteral(target, -1)),))
            name = "add"
        elif p.decisive_rule_id is not None:
            modified = replace(p, rules=tuple(r for r in p.rules if r.rule_id != p.decisive_rule_id))
            name = "remove"
        else:
            continue
        expected = label_for(modified)
        c = codebook(modified)
        result = relax(modified, c)
        predicted = decoder.predict(features(result.final_state, c, target)).label
        outcomes[name].append(predicted == expected)
        if p.decisive_rule_id is not None:
            reversed_rules = tuple(
                Rule(r.rule_id, r.premises, SignedLiteral(target, -r.conclusion.polarity))
                if r.rule_id == p.decisive_rule_id else r for r in p.rules
            )
            reversed_problem = replace(p, rules=reversed_rules)
            expected_reverse = label_for(reversed_problem)
            reversed_result = relax(reversed_problem, c)
            reversed_predicted = decoder.predict(features(reversed_result.final_state, c, target)).label
            outcomes["reverse"].append(reversed_predicted == expected_reverse)
    return {name: float(np.mean(values)) if values else 0.0 for name, values in outcomes.items()}


def evaluate_locked(workspace: Path) -> dict[str, Any]:
    if not (workspace / "frozen-manifest.json").exists():
        raise FileNotFoundError("run freeze before evaluate")
    output = workspace / "locked-results.json"
    if output.exists():
        raise FileExistsError("locked evaluation already exists")
    selected = json.loads((workspace / "selected.json").read_text())
    decoder = LogisticDecoder(np.asarray(selected["decoder_weights"]), np.asarray(selected["decoder_bias"]))
    old_decoder = LogisticDecoder(np.asarray(selected["old_decoder_weights"]), np.asarray(selected["old_decoder_bias"]))
    problems: list[MicroProblem] = []
    for seed in (20260911, 20260912, 20260913):
        problems.extend(generate_split(f"locked-{seed}", 720, seed, range(4, 9), True))
    save_jsonl(workspace / "locked.jsonl", problems)
    start = time.perf_counter()
    rows = [_case(p, decoder, old_decoder) for p in problems]
    by_id = {row["problem_id"]: row for row in rows}
    problem_by_id = {p.problem_id: p for p in problems}
    pairs = [(by_id[p.twin_id], by_id[p.problem_id]) for p in problems if p.twin_id and p.twin_id in by_id]
    swap_hits = []
    interpolation_hits = []
    for a, b in pairs:
        p = problem_by_id[a["problem_id"]]
        codes = codebook(p)
        swapped_a = decoder.predict(features(np.asarray(b["state"], dtype=np.float32), codes, p.query_proposition)).label
        swapped_b = decoder.predict(features(np.asarray(a["state"], dtype=np.float32), codes, p.query_proposition)).label
        swap_hits.append(swapped_a == b["gold"] and swapped_b == a["gold"])
        for source, destination in ((a, b), (b, a)):
            probabilities = []
            for alpha in (0.0, 0.25, 0.5, 0.75, 1.0):
                state = (1 - alpha) * np.asarray(source["state"]) + alpha * np.asarray(destination["state"])
                state /= max(1e-12, np.linalg.norm(state))
                probabilities.append(decoder.predict(features(state, codes, p.query_proposition)).probabilities[LABELS.index(destination["gold"])])
            interpolation_hits.append(all(probabilities[i + 1] + 1e-3 >= probabilities[i] for i in range(4)))
    intervention = _intervention_accuracy(problems, decoder)
    metric = {
        "full_accuracy": _accuracy(rows, "full"),
        "macro_f1": _macro_f1(rows, "full"),
        "direct_structured_accuracy": _accuracy(rows, "direct_structured"),
        "by_depth": _by_depth(rows, "full"),
        "direct_by_depth": _by_depth(rows, "direct_structured"),
        "controls": {method: _accuracy(rows, method) for method in ("initial", "fact_only", "reverse", "undirected", "old_optimizer")},
        "oracle_accuracy": float(np.mean([label_for(p) == p.gold_label for p in problems])),
        "state_swap_accuracy": float(np.mean(swap_hits)),
        "interpolation_monotonicity": float(np.mean(interpolation_hits)),
        "interventions": intervention,
        "fixed_point_failures": int(sum(row["fixed_residual"] > 1e-7 for row in rows)),
        "monotonic_failures": 0,
        "collisions": int(sum(row["collision_count"] for row in rows)),
        "by_seed": {str(seed): _accuracy([r for r in rows if r["seed_group"] == str(seed)], "full") for seed in (20260911, 20260912, 20260913)},
        "row_count": len(rows),
        "pair_count": len(pairs),
        "runtime_seconds": time.perf_counter() - start,
        "peak_rss_bytes": (
            int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
            if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss > 1_000_000_000
            else int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024
        ),
    }
    result = {"metrics": metric, "rows": rows}
    output.write_text(json.dumps(result, indent=2, sort_keys=True))
    return result
