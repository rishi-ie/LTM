from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from .decode import LogisticDecoder, features, train_decoder
from .field import make_codebook, supports
from .generator import generate_split, save_jsonl
from .optimize import optimize
from .oracle import label_for
from .schemas import FieldConfig, MicroProblem


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _field_config(row: dict[str, Any]) -> FieldConfig:
    return FieldConfig(
        fact_weight=float(row["fact_weight"]),
        rule_weight=float(row["rule_weight"]),
        sparsity_weight=float(row["sparsity_weight"]),
        dimension=128,
        propositions=24,
    )


def _config_dict(config: FieldConfig) -> dict[str, float | int]:
    return {
        "fact_weight": config.fact_weight,
        "rule_weight": config.rule_weight,
        "sparsity_weight": config.sparsity_weight,
        "dimension": config.dimension,
        "propositions": config.propositions,
        "kappa": config.kappa,
        "bias": config.bias,
        "exclusion_weight": config.exclusion_weight,
        "norm_weight": config.norm_weight,
    }


def _threshold_label(pos: float, neg: float) -> str:
    if pos >= 0.65 and neg < 0.35:
        return "entailed"
    if neg >= 0.65 and pos < 0.35:
        return "contradicted"
    return "unknown"


def _case_result(problem: MicroProblem, config: FieldConfig, decoder: LogisticDecoder | None = None) -> dict[str, Any]:
    codes = make_codebook(problem, config)
    full = optimize(problem, config, codes=codes)
    no_rule = optimize(problem, config, codes=codes, include_rules=False)
    undirected = optimize(problem, config, codes=codes, undirected=True)
    h0 = full.initial_state
    s0 = supports(h0, codes, config)
    bary = np.sum(np.asarray([codes[0 if f.polarity == 1 else 1, f.proposition] for f in problem.facts]), axis=0)
    bary_norm = float(np.linalg.norm(bary))
    bary = (bary / bary_norm * 0.5).astype(np.float32) if bary_norm else np.zeros_like(full.final_state)
    sf = supports(full.final_state, codes, config)
    sr = supports(no_rule.final_state, codes, config)
    su = supports(undirected.final_state, codes, config)
    sb = supports(bary, codes, config)
    q = problem.query_proposition
    labels = {
        "full": decoder.predict(features(full.final_state, codes, q)).label if decoder else _threshold_label(sf[0, q], sf[1, q]),
        "initial": _threshold_label(s0[0, q], s0[1, q]),
        "fact_only": decoder.predict(features(no_rule.final_state, codes, q)).label if decoder else _threshold_label(sr[0, q], sr[1, q]),
        "undirected": decoder.predict(features(undirected.final_state, codes, q)).label if decoder else _threshold_label(su[0, q], su[1, q]),
        "barycenter": _threshold_label(sb[0, q], sb[1, q]),
    }
    return {
        "problem_id": problem.problem_id,
        "twin_id": problem.twin_id,
        "gold": problem.gold_label,
        "depth": problem.proof_depth,
        "predictions": labels,
        "supports": {
            "full": [float(sf[0, q]), float(sf[1, q])],
            "initial": [float(s0[0, q]), float(s0[1, q])],
            "fact_only": [float(sr[0, q]), float(sr[1, q])],
            "undirected": [float(su[0, q]), float(su[1, q])],
            "barycenter": [float(sb[0, q]), float(sb[1, q])],
        },
        "energy": [full.initial_energy, full.final_energy],
        "evaluations": len(full.trace),
        "convergence": full.convergence_reason,
        "state": full.final_state.tolist(),
        "codebook": codes.tolist(),
    }


def _accuracy(rows: list[dict[str, Any]], method: str) -> float:
    return float(np.mean([r["predictions"][method] == r["gold"] for r in rows])) if rows else 0.0


def _by_depth(rows: list[dict[str, Any]], method: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for depth in sorted({r["depth"] for r in rows}):
        subset = [r for r in rows if r["depth"] == depth]
        out[str(depth)] = _accuracy(subset, method)
    return out


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def develop(workspace: Path, propositions: int = 24) -> dict[str, Any]:
    workspace.mkdir(parents=True, exist_ok=True)
    train = generate_split("train", 4080, 1729, propositions, range(1, 4), False)
    dev = generate_split("dev", 540, 1730, propositions, range(1, 6), True)
    save_jsonl(workspace / "train.jsonl", train)
    save_jsonl(workspace / "dev.jsonl", dev)
    candidates = [FieldConfig(f, r, s, propositions=propositions) for f in (16.0, 32.0) for r in (8.0, 16.0, 32.0) for s in (0.01, 0.03)]
    grid = []
    selected = None
    for config in candidates:
        rows = [_case_result(p, config) for p in dev]
        item = {
            "config": _config_dict(config),
            "accuracy": _accuracy(rows, "full"),
            "depth5": _accuracy([r for r in rows if r["depth"] == 5], "full"),
            "twin": _accuracy([r for r in rows if r["twin_id"]], "full"),
            "collision": float(np.mean([r["supports"]["full"][0] > 0.7 and r["supports"]["full"][1] > 0.7 for r in rows])),
            "evaluations": float(np.mean([r["evaluations"] for r in rows])),
        }
        grid.append(item)
        key = (-item["accuracy"], -item["depth5"], -item["twin"], item["collision"], item["evaluations"], config.fact_weight, config.rule_weight, config.sparsity_weight)
        if selected is None or key < selected[0]:
            selected = (key, item)
    assert selected is not None
    selected_config = _field_config(selected[1]["config"])
    train_rows = [_case_result(p, selected_config) for p in train]
    x_train = np.asarray([features(np.asarray(r["state"], dtype=np.float32), np.asarray(r["codebook"], dtype=np.float32), p.query_proposition) for r, p in zip(train_rows, train)])
    labels = [p.gold_label for p in train]
    best_decoder = None
    best_score = -1.0
    for lr in (0.01, 0.05):
        for l2 in (0.0, 0.001):
            decoder = train_decoder(x_train, labels, lr, l2)
            dev_rows = [_case_result(p, selected_config, decoder) for p in dev]
            score = _accuracy(dev_rows, "full")
            if score > best_score:
                best_score, best_decoder = score, decoder
    assert best_decoder is not None
    selected_payload = {
        "field": _config_dict(selected_config),
        "decoder_weights": best_decoder.weights.tolist(),
        "decoder_bias": best_decoder.bias.tolist(),
        "development_decoder_accuracy": best_score,
        "grid": grid,
    }
    (workspace / "selected.json").write_text(json.dumps(selected_payload, indent=2, sort_keys=True))
    return {"grid": grid, "selected": selected_payload, "train_count": len(train), "dev_count": len(dev)}


def freeze(workspace: Path) -> dict[str, Any]:
    selected = workspace / "selected.json"
    train = workspace / "train.jsonl"
    dev = workspace / "dev.jsonl"
    if not all(p.exists() for p in (selected, train, dev)):
        raise FileNotFoundError("run develop before freeze")
    manifest = {
        "experiment": "MICRO-LTM-1",
        "selected_sha256": sha256_file(selected),
        "train_sha256": sha256_file(train),
        "dev_sha256": sha256_file(dev),
        "frozen_at": time.time(),
    }
    (workspace / "frozen-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return manifest


def evaluate_locked(workspace: Path) -> dict[str, Any]:
    if not (workspace / "frozen-manifest.json").exists():
        raise FileNotFoundError("run freeze before evaluate")
    output = workspace / "locked-results.json"
    if output.exists():
        raise FileExistsError("locked evaluation already exists")
    selected = _load_json(workspace / "selected.json")
    config = _field_config(selected["field"])
    decoder = LogisticDecoder(np.asarray(selected["decoder_weights"]), np.asarray(selected["decoder_bias"]))
    problems: list[MicroProblem] = []
    for seed in (20260802, 20260803, 20260804):
        problems.extend(generate_split(f"locked-{seed}", 720, seed, 24, range(4, 9), True))
    save_jsonl(workspace / "locked.jsonl", problems)
    rows = [_case_result(p, config, decoder) for p in problems]
    by_id = {r["problem_id"]: r for r in rows}
    pairs = []
    for p in problems:
        if p.twin_id and p.twin_id in by_id:
            pairs.append((by_id[p.twin_id], by_id[p.problem_id]))

    shuffled_hits = []
    mismatch_hits = []
    for index, row in enumerate(rows):
        other = rows[(index + 1) % len(rows)]
        query = next(p.query_proposition for p in problems if p.problem_id == row["problem_id"])
        own_codes = np.asarray(row["codebook"], dtype=np.float32)
        other_codes = np.asarray(other["codebook"], dtype=np.float32)
        shuffled = decoder.predict(features(np.asarray(other["state"], dtype=np.float32), own_codes, query)).label
        mismatched = decoder.predict(features(np.asarray(row["state"], dtype=np.float32), other_codes, query)).label
        shuffled_hits.append(shuffled == row["gold"])
        mismatch_hits.append(mismatched == row["gold"])
    full = _accuracy(rows, "full")
    def swapped_ok(a: dict[str, Any], b: dict[str, Any]) -> bool:
        # The target and codebook are shared by a counterfactual pair. Swapping
        # only the optimized states is therefore a direct causal readout test.
        codes = np.asarray(a["codebook"], dtype=np.float32)
        qa = int(next(p.query_proposition for p in problems if p.problem_id == a["problem_id"]))
        qb = int(next(p.query_proposition for p in problems if p.problem_id == b["problem_id"]))
        pa = decoder.predict(features(np.asarray(b["state"], dtype=np.float32), codes, qa)).label
        pb = decoder.predict(features(np.asarray(a["state"], dtype=np.float32), codes, qb)).label
        return pa == b["gold"] and pb == a["gold"]

    metrics = {
        "full_accuracy": full,
        "by_depth": _by_depth(rows, "full"),
        "controls": {method: _accuracy(rows, method) for method in ("initial", "barycenter", "fact_only", "undirected")},
        "oracle_accuracy": float(np.mean([label_for(p) == p.gold_label for p in problems])),
        "energy_increases": int(sum(r["energy"][1] > r["energy"][0] + 1e-8 for r in rows)),
        "numerical_failures": int(sum(r["convergence"] == "numerical_failure" for r in rows)),
        "state_swap_accuracy": float(np.mean([swapped_ok(a, b) for a, b in pairs])) if pairs else 0.0,
        "shuffled_state_accuracy": float(np.mean(shuffled_hits)),
        "mismatched_codebook_accuracy": float(np.mean(mismatch_hits)),
        "by_seed": {
            str(seed): _accuracy([r for r in rows if f"locked-{seed}-" in r["problem_id"]], "full")
            for seed in (20260802, 20260803, 20260804)
        },
        "row_count": len(rows),
        "pair_count": len(pairs),
    }
    result = {"metrics": metrics, "rows": rows}
    output.write_text(json.dumps(result, indent=2, sort_keys=True))
    return result
