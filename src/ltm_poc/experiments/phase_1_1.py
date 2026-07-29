"""Phase 1.1 development grid, held-out controls, and decision gate."""

import hashlib
import json
import resource
import time
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import numpy as np

from ltm_poc.config import load_workspace_config
from ltm_poc.devices import resolve_device
from ltm_poc.experiments.common import chunks_from_documents, quality
from ltm_poc.experiments.multi_state import (
    LatentSetField,
    SetOptimizerConfig,
    initialize_states,
    mmr_indices,
    optimize_set,
    resolve_set_evidence,
)
from ltm_poc.field import LatentField
from ltm_poc.models import load_embedding_model
from ltm_poc.optimize import mean_shift, optimize
from ltm_poc.retrieve import retrieve


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _prepare(model: Any, suite_path: Path) -> dict[str, Any]:
    scenarios = json.loads(suite_path.read_text(encoding="utf-8"))
    documents = {
        doc_id: text
        for scenario in scenarios
        for doc_id, text in scenario["documents"].items()
    }
    chunks = chunks_from_documents(documents)
    queries = [
        (scenario, offset, query)
        for scenario in scenarios
        for offset, query in enumerate(scenario["queries"])
    ]
    texts = [chunk.text for chunk in chunks] + [query for _, _, query in queries]
    encoded = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
    return {
        "scenarios": scenarios,
        "chunks": chunks,
        "queries": queries,
        "vectors": np.asarray(encoded[: len(chunks)], dtype=np.float32),
        "query_vectors": np.asarray(encoded[len(chunks) :], dtype=np.float32),
        "corpus_sha256": hashlib.sha256(
            json.dumps(documents, sort_keys=True).encode("utf-8")
        ).hexdigest(),
    }


def _multi(
    field: LatentField,
    chunk_by_id: dict[str, Any],
    config: SetOptimizerConfig,
    limit: int,
    query_only: bool = False,
) -> tuple[list[str], dict[str, Any]]:
    active_chunks = [chunk_by_id[item.chunk_id] for item in field.evidence]
    states = initialize_states(field, active_chunks, config, query_only=query_only)
    set_field = LatentSetField(field, config.diversity_weight, config.similarity_cap)
    started = time.perf_counter()
    result = optimize_set(set_field, states, config)
    latency = (time.perf_counter() - started) * 1000
    final_states = np.asarray(result.final_states, dtype=np.float64)
    evidence = resolve_set_evidence(field, final_states, limit)
    return [item.chunk_id for item in evidence], {
        "latency_ms": latency,
        "set_evaluations": result.set_evaluations,
        "slot_energy_evaluations": result.slot_energy_evaluations,
        "initial_energy": result.initial_energy,
        "final_energy": result.final_energy,
        "unit_norm": bool(
            np.allclose(np.linalg.norm(final_states, axis=1), 1.0, atol=1e-6)
        ),
    }


def _evaluate_multi(
    prepared: dict[str, Any],
    workspace_config: Any,
    set_config: SetOptimizerConfig,
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    chunks = prepared["chunks"]
    vectors = prepared["vectors"]
    chunk_by_id = {chunk.chunk_id: chunk for chunk in chunks}
    local = workspace_config.model_copy(
        update={
            "active_candidates": min(workspace_config.active_candidates, len(chunks)),
            "evidence_limit": min(4, len(chunks)),
        }
    )
    rows = []
    for index, (scenario, offset, _) in enumerate(prepared["queries"]):
        query = prepared["query_vectors"][index]
        field = LatentField.construct(query, vectors, chunks, local)
        ids, diagnostic = _multi(field, chunk_by_id, set_config, local.evidence_limit)
        recall, precision = quality(ids, set(scenario["gold"]))
        rows.append(
            {
                "case_id": f"{scenario['id']}-{offset + 1:02d}",
                "domain": scenario["id"],
                "category": scenario.get("category", "development"),
                "recall_at_4": recall,
                "precision_at_4": precision,
                "ids": ids,
                **diagnostic,
            }
        )
    return rows, _summary(rows)


def _summary(rows: list[dict[str, Any]]) -> dict[str, float]:
    numeric = (
        "recall_at_4",
        "precision_at_4",
        "latency_ms",
        "set_evaluations",
        "slot_energy_evaluations",
    )
    return {
        metric: float(np.mean([row.get(metric, 0.0) for row in rows]))
        for metric in numeric
    }


def _grid() -> list[SetOptimizerConfig]:
    return [
        SetOptimizerConfig(
            slots=slots,
            seed_mix=seed_mix,
            diversity_weight=weight,
            similarity_cap=cap,
        )
        for slots in (2, 4)
        for seed_mix in (0.15, 0.30)
        for weight in (0.25, 0.75, 1.50)
        for cap in (0.60, 0.75)
    ]


def _selected(grid: list[dict[str, Any]]) -> dict[str, Any]:
    return min(
        grid,
        key=lambda item: (
            -item["summary"]["recall_at_4"],
            -item["summary"]["precision_at_4"],
            round(item["summary"]["latency_ms"], 1),
            item["config"]["slots"],
            item["config"]["diversity_weight"],
            item["config"]["similarity_cap"],
        ),
    )


def _baseline_rows(
    prepared: dict[str, Any],
    workspace_config: Any,
    selected: SetOptimizerConfig,
) -> list[dict[str, Any]]:
    chunks, vectors = prepared["chunks"], prepared["vectors"]
    chunk_by_id = {chunk.chunk_id: chunk for chunk in chunks}
    local = workspace_config.model_copy(
        update={
            "active_candidates": min(workspace_config.active_candidates, len(chunks)),
            "evidence_limit": min(4, len(chunks)),
        }
    )
    rows: list[dict[str, Any]] = []
    for index, (scenario, offset, _) in enumerate(prepared["queries"]):
        query = prepared["query_vectors"][index]
        gold = set(scenario["gold"])
        field = LatentField.construct(query, vectors, chunks, local)
        started = time.perf_counter()
        _, direct = retrieve(query, vectors, chunks, local.evidence_limit)
        methods: dict[str, tuple[list[str], dict[str, Any]]] = {
            "direct": (
                [item.chunk_id for item in direct],
                {"latency_ms": (time.perf_counter() - started) * 1000},
            )
        }
        started = time.perf_counter()
        mmr = mmr_indices(
            query,
            vectors,
            chunks,
            local.evidence_limit,
            selected.seed_pool,
            selected.mmr_lambda,
        )
        methods["mmr"] = (
            [chunks[item].chunk_id for item in mmr],
            {"latency_ms": (time.perf_counter() - started) * 1000},
        )
        started = time.perf_counter()
        shifted = mean_shift(field)
        _, shifted_evidence = retrieve(
            shifted.astype(np.float32), vectors, chunks, local.evidence_limit
        )
        methods["mean_shift"] = (
            [item.chunk_id for item in shifted_evidence],
            {"latency_ms": (time.perf_counter() - started) * 1000},
        )
        started = time.perf_counter()
        single = optimize(field, local)
        _, single_evidence = retrieve(
            np.asarray(single.final_state, dtype=np.float32),
            vectors,
            chunks,
            local.evidence_limit,
        )
        methods["single_latent"] = (
            [item.chunk_id for item in single_evidence],
            {"latency_ms": (time.perf_counter() - started) * 1000},
        )
        methods["multi_latent"] = _multi(
            field, chunk_by_id, selected, local.evidence_limit
        )
        methods["ablation_no_diversity"] = _multi(
            field,
            chunk_by_id,
            replace(selected, diversity_weight=0.0),
            local.evidence_limit,
        )
        methods["ablation_query_init"] = _multi(
            field,
            chunk_by_id,
            selected,
            local.evidence_limit,
            query_only=True,
        )
        for method, (ids, diagnostic) in methods.items():
            recall, precision = quality(ids, gold)
            rows.append(
                {
                    "case_id": f"{scenario['id']}-{offset + 1:02d}",
                    "domain": scenario["id"],
                    "category": scenario.get("category", "held_out"),
                    "method": method,
                    "recall_at_4": recall,
                    "precision_at_4": precision,
                    "ids": ids,
                    **diagnostic,
                }
            )
    return rows


def _bootstrap_interval(
    direct: list[float], multi: list[float], samples: int = 2000
) -> list[float]:
    differences = np.asarray(multi) - np.asarray(direct)
    rng = np.random.default_rng(1729)
    means = [
        float(np.mean(rng.choice(differences, size=len(differences), replace=True)))
        for _ in range(samples)
    ]
    return [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))]


def _classify(rows: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    methods = {
        method: [row for row in rows if row["method"] == method]
        for method in ("direct", "mmr", "multi_latent")
    }
    summaries = {name: _summary(items) for name, items in methods.items()}
    direct = [row["recall_at_4"] for row in methods["direct"]]
    multi = [row["recall_at_4"] for row in methods["multi_latent"]]
    interval = _bootstrap_interval(direct, multi)
    domain_losses = []
    for domain in sorted({row["domain"] for row in rows}):
        direct_mean = np.mean(
            [row["recall_at_4"] for row in methods["direct"] if row["domain"] == domain]
        )
        multi_mean = np.mean(
            [
                row["recall_at_4"]
                for row in methods["multi_latent"]
                if row["domain"] == domain
            ]
        )
        domain_losses.append(float(direct_mean - multi_mean))
    multi_rows = methods["multi_latent"]
    numerical_failures = sum(
        not row.get("unit_norm", True)
        or row.get("final_energy", 0) > row.get("initial_energy", 0) + 1e-4
        or row.get("set_evaluations", 0) > 16
        for row in multi_rows
    )
    mmr_by_case = {row["case_id"]: row["ids"] for row in methods["mmr"]}
    changed = np.mean([row["ids"] != mmr_by_case[row["case_id"]] for row in multi_rows])
    peak_rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)
    direct_summary, mmr_summary, multi_summary = (
        summaries["direct"],
        summaries["mmr"],
        summaries["multi_latent"],
    )
    common = (
        multi_summary["recall_at_4"] - direct_summary["recall_at_4"] >= 0.05
        and direct_summary["precision_at_4"] - multi_summary["precision_at_4"] <= 0.05
        and interval[0] > 0
        and max(domain_losses) <= 0.10
        and numerical_failures == 0
        and changed >= 0.10
        and peak_rss_mb < 8192
    )
    if numerical_failures:
        classification = "D"
    elif common:
        classification = (
            "A"
            if multi_summary["recall_at_4"] - mmr_summary["recall_at_4"] >= 0.02
            else "B+"
        )
    else:
        classification = "B"
    gate = {
        "bootstrap_recall_difference_95pct": interval,
        "max_domain_recall_loss": max(domain_losses),
        "numerical_failures": numerical_failures,
        "evidence_change_from_mmr": float(changed),
        "peak_rss_mb": peak_rss_mb,
    }
    return classification, {"summary": summaries, "gate": gate}


def run(
    workspace: Path, dev_suite: Path, test_suite: Path, output: Path
) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    config = load_workspace_config(workspace / "workspace.json")
    model = load_embedding_model(
        Path(config.embedding_model_path), resolve_device(config.device)
    )
    dev = _prepare(model, dev_suite)
    grid = []
    for candidate in _grid():
        _, summary = _evaluate_multi(dev, config, candidate)
        grid.append({"config": asdict(candidate), "summary": summary})
    selected_item = _selected(grid)
    selected_path = output / "phase-1.1-selected-config.json"
    (output / "phase-1.1-dev-grid.json").write_text(
        json.dumps(grid, indent=2) + "\n", encoding="utf-8"
    )
    selected_path.write_text(
        json.dumps(selected_item, indent=2) + "\n", encoding="utf-8"
    )
    selected = SetOptimizerConfig(**selected_item["config"])
    test = _prepare(model, test_suite)
    rows = _baseline_rows(test, config, selected)
    classification, decision = _classify(rows)
    decision["summary"] = {
        method: _summary([row for row in rows if row["method"] == method])
        for method in (
            "direct",
            "mmr",
            "mean_shift",
            "single_latent",
            "multi_latent",
            "ablation_no_diversity",
            "ablation_query_init",
        )
    }
    result = {
        "classification": classification,
        "case_count": len(test["queries"]),
        "model_id": config.embedding_model_id,
        "model_revision": config.embedding_revision,
        "dev_suite_sha256": _sha256(dev_suite),
        "test_suite_sha256": _sha256(test_suite),
        "test_corpus_sha256": test["corpus_sha256"],
        "selected_config": asdict(selected),
        **decision,
        "rows": rows,
    }
    (output / "phase-1.1-test-results.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    _write_markdown(result, output / "phase-1.1-test-results.md")
    return result


def _write_markdown(result: dict[str, Any], path: Path) -> None:
    gate = result["gate"]
    lines = [
        "# Phase 1.1 Held-Out Results",
        "",
        f"Classification: **{result['classification']}**",
        "",
        "| Method | Recall@4 | Precision@4 | Latency ms |",
        "| --- | ---: | ---: | ---: |",
    ]
    for method, summary in result["summary"].items():
        lines.append(
            f"| {method} | {summary['recall_at_4']:.3f} | "
            f"{summary['precision_at_4']:.3f} | {summary['latency_ms']:.3f} |"
        )
    lines.extend(
        [
            "",
            f"Recall difference 95% CI: {gate['bootstrap_recall_difference_95pct']}",
            f"Maximum domain recall loss: {gate['max_domain_recall_loss']:.3f}",
            f"Evidence change from MMR: {gate['evidence_change_from_mmr']:.3f}",
            f"Numerical failures: {gate['numerical_failures']}",
            f"Peak RSS: {gate['peak_rss_mb']:.1f} MB",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
