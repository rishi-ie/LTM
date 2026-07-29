"""Phase 1.2 equilibrium grid, locked evaluation, and scaling checks."""

from __future__ import annotations

import hashlib
import json
import resource
import time
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from ltm_poc.config import load_workspace_config
from ltm_poc.devices import resolve_device
from ltm_poc.experiments.common import quality
from ltm_poc.experiments.equilibrium import (
    EquilibriumConfig,
    EquilibriumField,
    SemanticFieldHierarchy,
    build_evidence_bundle,
    optimize_equilibrium,
)
from ltm_poc.field import LatentField
from ltm_poc.models import load_embedding_model
from ltm_poc.optimize import optimize
from ltm_poc.retrieve import retrieve
from ltm_poc.schemas import ChunkRecord


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _chunk(
    chunk_id: str, text: str, metadata: dict[str, Any] | None = None
) -> ChunkRecord:
    return ChunkRecord(
        chunk_id=chunk_id,
        record_id=chunk_id,
        source_path=chunk_id,
        source_kind="text",
        text=text,
        char_start=0,
        char_end=len(text),
        token_start=0,
        token_end=max(1, len(text.split())),
        token_count=max(1, len(text.split())),
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
        metadata=metadata or {},
    )


def _load_development(paths: Iterable[Path]) -> dict[str, Any]:
    documents: dict[str, str] = {}
    cases: list[dict[str, Any]] = []
    expanded: list[Path] = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and "sources" in payload:
            expanded.extend(path.parent / source for source in payload["sources"])
        else:
            expanded.append(path)
    for path in expanded:
        for scenario in json.loads(path.read_text(encoding="utf-8")):
            documents.update(scenario["documents"])
            for offset, query in enumerate(scenario["queries"]):
                cases.append(
                    {
                        "id": f"{scenario['id']}-{offset + 1:02d}",
                        "domain": scenario["id"],
                        "category": "development",
                        "query": query,
                        "high": list(scenario["gold"]),
                        "low": [],
                        "conflicts": [],
                    }
                )
    return {
        "chunks": [_chunk(key, value) for key, value in sorted(documents.items())],
        "cases": cases,
    }


def _load_held_out(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("locked") is not True:
        raise ValueError("held-out equilibrium suite must be marked locked")
    chunks: list[ChunkRecord] = []
    cases: list[dict[str, Any]] = []
    for domain in payload["domains"]:
        for chunk_id, item in domain["documents"].items():
            chunks.append(_chunk(chunk_id, item["text"], item["metadata"]))
        for case in domain["cases"]:
            cases.append({**case, "domain": domain["id"]})
    chunks.sort(key=lambda item: item.chunk_id)
    return {"chunks": chunks, "cases": cases}


def _encode(model: Any, prepared: dict[str, Any]) -> dict[str, Any]:
    chunks, cases = prepared["chunks"], prepared["cases"]
    encoded = model.encode(
        [chunk.text for chunk in chunks] + [case["query"] for case in cases],
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return {
        **prepared,
        "vectors": np.asarray(encoded[: len(chunks)], dtype=np.float64),
        "queries": np.asarray(encoded[len(chunks) :], dtype=np.float64),
    }


def _ids(bundle: dict[str, Any]) -> list[str]:
    return [item["chunk_id"] for item in bundle["evidence"]]


def _residual_metrics(
    field: EquilibriumField,
    state: np.ndarray,
    high: set[str],
    chunks: list[ChunkRecord],
) -> tuple[float, float]:
    residuals = field.residuals(state)
    high_residuals = []
    for index, element in enumerate(field.frontier.elements):
        if element.kind != "exact":
            continue
        chunk_id = chunks[element.member_indices[0]].chunk_id
        if chunk_id in high:
            high_residuals.append(float(residuals[index]))
    worst = max(high_residuals) if high_residuals else 0.0
    average = float(field.average_weights @ residuals)
    return worst, average


def _run_equilibrium(
    hierarchy: SemanticFieldHierarchy,
    query: np.ndarray,
    config: EquilibriumConfig,
    chunks: list[ChunkRecord],
    hierarchical: bool,
) -> tuple[EquilibriumField, Any, dict[str, Any], float]:
    frontier = (
        hierarchy.compile_frontier(query)
        if hierarchical
        else hierarchy.exact_frontier(query)
    )
    field = EquilibriumField(frontier, config)
    started = time.perf_counter()
    result = optimize_equilibrium(field)
    latency = (time.perf_counter() - started) * 1000
    bundle = build_evidence_bundle(field, result, chunks)
    result = replace(
        result,
        evidence=bundle["evidence"],
        approximation_diagnostics={
            "frontier_elements": len(frontier.elements),
            "exact_constraints": frontier.exact_count,
            "aggregate_constraints": frontier.aggregate_count,
        },
    )
    return field, result, bundle, latency


def _grid() -> list[EquilibriumConfig]:
    return [
        EquilibriumConfig(max_weight=max_weight, query_anchor=query_anchor, beta=beta)
        for max_weight in (0.5, 1.0, 2.0)
        for query_anchor in (0.5, 1.0, 2.0)
        for beta in (5.0, 10.0)
    ]


def _development_grid(
    prepared: dict[str, Any],
    hierarchy: SemanticFieldHierarchy,
) -> list[dict[str, Any]]:
    chunks = prepared["chunks"]
    rows = []
    for config in _grid():
        metrics = []
        for case, query in zip(prepared["cases"], prepared["queries"]):
            exact_field, exact_result, _, exact_ms = _run_equilibrium(
                hierarchy, query, config, chunks, False
            )
            hierarchical_field, hierarchical_result, _, hierarchical_ms = (
                _run_equilibrium(hierarchy, query, config, chunks, True)
            )
            exact_state = np.asarray(exact_result.final_state)
            hierarchical_state = np.asarray(hierarchical_result.final_state)
            worst, average = _residual_metrics(
                exact_field, exact_state, set(case["high"]), chunks
            )
            exact_energy = exact_field.energy_and_gradient(exact_state)[0]
            approximate_energy = exact_field.energy_and_gradient(hierarchical_state)[0]
            metrics.append(
                {
                    "worst_high_weight_residual": worst,
                    "average_weighted_residual": average,
                    "prompt_cosine": float(exact_state @ query),
                    "approximation_error": abs(approximate_energy - exact_energy)
                    / max(abs(exact_energy), 1e-12),
                    "latency_ms": exact_ms + hierarchical_ms,
                    "hierarchy_elements": len(hierarchical_field.frontier.elements),
                }
            )
        summary = {
            key: float(np.mean([row[key] for row in metrics])) for key in metrics[0]
        }
        rows.append({"config": asdict(config), "summary": summary})
    return rows


def _select(grid: list[dict[str, Any]]) -> dict[str, Any]:
    return min(
        grid,
        key=lambda item: (
            item["summary"]["worst_high_weight_residual"],
            item["summary"]["average_weighted_residual"],
            -item["summary"]["prompt_cosine"],
            item["summary"]["approximation_error"],
            round(item["summary"]["latency_ms"], 1),
            item["config"]["max_weight"],
            -item["config"]["query_anchor"],
            item["config"]["beta"],
        ),
    )


def _evaluate_test(
    prepared: dict[str, Any],
    hierarchy: SemanticFieldHierarchy,
    config: EquilibriumConfig,
    workspace_config: Any,
) -> list[dict[str, Any]]:
    chunks, vectors = prepared["chunks"], prepared["vectors"]
    local = workspace_config.model_copy(
        update={
            "active_candidates": min(workspace_config.active_candidates, len(chunks)),
            "evidence_limit": min(4, len(chunks)),
        }
    )
    rows: list[dict[str, Any]] = []
    for case, query in zip(prepared["cases"], prepared["queries"]):
        gold = set(case["high"]) | set(case["low"])
        started = time.perf_counter()
        _, direct_items = retrieve(query, vectors, chunks, 4)
        direct_ms = (time.perf_counter() - started) * 1000
        direct_ids = [item.chunk_id for item in direct_items]
        direct_recall, direct_precision = quality(direct_ids, gold)
        rows.append(
            {
                "case_id": case["id"],
                "domain": case["domain"],
                "category": case["category"],
                "method": "prompt_state",
                "ids": direct_ids,
                "recall_at_4": direct_recall,
                "precision_at_4": direct_precision,
                "latency_ms": 0.0,
            }
        )
        rows.append(
            {
                **rows[-1],
                "method": "direct",
                "latency_ms": direct_ms,
            }
        )
        exact_field = EquilibriumField(hierarchy.exact_frontier(query), config)
        barycenter = exact_field.barycenter()
        bary_bundle = build_evidence_bundle(
            exact_field,
            replace(
                optimize_equilibrium(
                    EquilibriumField(
                        exact_field.frontier, replace(config, max_weight=0.0)
                    )
                ),
                final_state=barycenter.tolist(),
                residuals=exact_field.residuals(barycenter).tolist(),
            ),
            chunks,
        )
        bary_ids = _ids(bary_bundle)
        bary_recall, bary_precision = quality(bary_ids, gold)
        bary_worst, bary_average = _residual_metrics(
            exact_field, barycenter, set(case["high"]), chunks
        )
        rows.append(
            {
                "case_id": case["id"],
                "domain": case["domain"],
                "category": case["category"],
                "method": "barycenter",
                "ids": bary_ids,
                "recall_at_4": bary_recall,
                "precision_at_4": bary_precision,
                "latency_ms": 0.0,
                "worst_high_weight_residual": bary_worst,
                "average_weighted_residual": bary_average,
                "prompt_cosine": float(barycenter @ query),
            }
        )
        density = LatentField.construct(query, vectors, chunks, local)
        started = time.perf_counter()
        density_result = optimize(density, local)
        _, density_items = retrieve(
            np.asarray(density_result.final_state), vectors, chunks, 4
        )
        density_ms = (time.perf_counter() - started) * 1000
        density_ids = [item.chunk_id for item in density_items]
        density_recall, density_precision = quality(density_ids, gold)
        rows.append(
            {
                "case_id": case["id"],
                "domain": case["domain"],
                "category": case["category"],
                "method": "density",
                "ids": density_ids,
                "recall_at_4": density_recall,
                "precision_at_4": density_precision,
                "latency_ms": density_ms,
            }
        )
        exact_field, exact_result, exact_bundle, exact_ms = _run_equilibrium(
            hierarchy, query, config, chunks, False
        )
        hierarchy_field, hierarchy_result, hierarchy_bundle, hierarchy_ms = (
            _run_equilibrium(hierarchy, query, config, chunks, True)
        )
        exact_state = np.asarray(exact_result.final_state)
        hierarchy_state = np.asarray(hierarchy_result.final_state)
        exact_energy = exact_field.energy_and_gradient(exact_state)[0]
        hierarchy_oracle_energy = exact_field.energy_and_gradient(hierarchy_state)[0]
        exact_ids, hierarchy_ids = _ids(exact_bundle), _ids(hierarchy_bundle)
        for method, state, result, ids, latency in (
            ("exact_equilibrium", exact_state, exact_result, exact_ids, exact_ms),
            (
                "hierarchical_equilibrium",
                hierarchy_state,
                hierarchy_result,
                hierarchy_ids,
                hierarchy_ms,
            ),
        ):
            recall, precision = quality(ids, gold)
            worst, average = _residual_metrics(
                exact_field, state, set(case["high"]), chunks
            )
            rows.append(
                {
                    "case_id": case["id"],
                    "domain": case["domain"],
                    "category": case["category"],
                    "method": method,
                    "ids": ids,
                    "recall_at_4": recall,
                    "precision_at_4": precision,
                    "latency_ms": latency,
                    "worst_high_weight_residual": worst,
                    "average_weighted_residual": average,
                    "prompt_cosine": float(state @ query),
                    "initial_energy": result.initial_energy,
                    "final_energy": result.final_energy,
                    "field_evaluations": result.field_evaluations,
                    "unit_norm": bool(
                        np.isclose(np.linalg.norm(state), 1.0, atol=1e-6)
                    ),
                    "exact_state_cosine": float(state @ exact_state),
                    "relative_oracle_energy_error": (
                        abs(hierarchy_oracle_energy - exact_energy)
                        / max(abs(exact_energy), 1e-12)
                        if method == "hierarchical_equilibrium"
                        else 0.0
                    ),
                    "exact_evidence_overlap": (
                        len(set(ids) & set(exact_ids)) / max(1, len(exact_ids))
                    ),
                    "unresolved_tensions": (
                        exact_bundle["unresolved_tensions"]
                        if method == "exact_equilibrium"
                        else hierarchy_bundle["unresolved_tensions"]
                    ),
                }
            )
    return rows


def _summary(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    methods = sorted({row["method"] for row in rows})
    keys = (
        "recall_at_4",
        "precision_at_4",
        "latency_ms",
        "worst_high_weight_residual",
        "average_weighted_residual",
        "prompt_cosine",
    )
    return {
        method: {
            key: float(
                np.mean(
                    [row[key] for row in rows if row["method"] == method and key in row]
                    or [0.0]
                )
            )
            for key in keys
        }
        for method in methods
    }


def _bootstrap(
    direct: list[float], equilibrium: list[float], samples: int = 2000
) -> list[float]:
    difference = np.asarray(equilibrium) - np.asarray(direct)
    rng = np.random.default_rng(1729)
    means = [
        float(np.mean(rng.choice(difference, len(difference), replace=True)))
        for _ in range(samples)
    ]
    return [
        float(np.percentile(means, 2.5)),
        float(np.percentile(means, 97.5)),
    ]


def _scale_checks(
    base_vectors: np.ndarray,
    base_metadata: list[dict[str, Any]],
    config: EquilibriumConfig,
) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    for count in (100, 1000, 10000):
        rng = np.random.default_rng(1729 + count)
        vectors = rng.normal(size=(count, base_vectors.shape[1]))
        vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
        metadata = [base_metadata[index % len(base_metadata)] for index in range(count)]
        started = time.perf_counter()
        hierarchy = SemanticFieldHierarchy.build(vectors, metadata)
        build_ms = (time.perf_counter() - started) * 1000
        query = vectors[0]
        started = time.perf_counter()
        frontier = hierarchy.compile_frontier(query)
        frontier_ms = (time.perf_counter() - started) * 1000
        started = time.perf_counter()
        hierarchical_field = EquilibriumField(frontier, config)
        hierarchical_result = optimize_equilibrium(hierarchical_field)
        optimization_ms = (time.perf_counter() - started) * 1000
        row: dict[str, Any] = {
            "count": count,
            "build_ms": build_ms,
            "frontier_ms": frontier_ms,
            "optimization_ms": optimization_ms,
            "frontier_elements": len(frontier.elements),
            "exact_constraints": frontier.exact_count,
            "aggregate_constraints": frontier.aggregate_count,
            "represented_once": len(frontier.represented_indices())
            == len(set(frontier.represented_indices()))
            == count,
            "peak_rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            / (1024 * 1024),
        }
        if count <= 1000:
            exact_field = EquilibriumField(hierarchy.exact_frontier(query), config)
            exact_result = optimize_equilibrium(exact_field)
            exact_state = np.asarray(exact_result.final_state)
            approximate_state = np.asarray(hierarchical_result.final_state)
            exact_energy = exact_field.energy_and_gradient(exact_state)[0]
            approximate_energy = exact_field.energy_and_gradient(approximate_state)[0]
            exact_residuals = exact_field.residuals(exact_state)
            approximate_residuals = exact_field.residuals(approximate_state)
            exact_top = set(np.argsort(exact_field.raw_weights)[-4:].tolist())
            hierarchical_exact = [
                index
                for index, element in enumerate(frontier.elements)
                if element.kind == "exact"
            ]
            approximate_top = {
                frontier.elements[index].member_indices[0]
                for index in sorted(
                    hierarchical_exact,
                    key=lambda item: (
                        -float(hierarchical_field.raw_weights[item]),
                        frontier.elements[item].element_id,
                    ),
                )[:4]
            }
            row.update(
                {
                    "final_state_cosine": float(exact_state @ approximate_state),
                    "relative_energy_error": abs(approximate_energy - exact_energy)
                    / max(abs(exact_energy), 1e-12),
                    "mean_residual_difference": float(
                        np.mean(np.abs(exact_residuals - approximate_residuals))
                    ),
                    "top_evidence_overlap": len(exact_top & approximate_top)
                    / max(1, len(exact_top)),
                }
            )
        if count == 10000:
            extra = rng.normal(size=(1000, base_vectors.shape[1]))
            extra /= np.linalg.norm(extra, axis=1, keepdims=True)
            expanded = SemanticFieldHierarchy.build(
                np.vstack([vectors, extra]),
                metadata + [{"priority": 0.01}] * len(extra),
            )
            expanded_result = optimize_equilibrium(
                EquilibriumField(expanded.compile_frontier(query), config)
            )
            row["irrelevant_expansion_cosine_drift"] = 1.0 - float(
                np.asarray(hierarchical_result.final_state)
                @ np.asarray(expanded_result.final_state)
            )
        checks[str(count)] = row
    return checks


def _controlled_checks(config: EquilibriumConfig) -> dict[str, float]:
    rng = np.random.default_rng(1729)
    movements = []
    for _ in range(100):
        vectors = rng.normal(size=(3, 384))
        vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
        query, target = vectors[0], vectors[1]
        ordinary = SemanticFieldHierarchy.build(vectors, [{"priority": 1.0}] * 3)
        stronger = SemanticFieldHierarchy.build(
            vectors,
            [{"priority": 1.0}, {"priority": 2.0}, {"priority": 1.0}],
        )
        ordinary_state = np.asarray(
            optimize_equilibrium(
                EquilibriumField(ordinary.exact_frontier(query), config)
            ).final_state
        )
        stronger_state = np.asarray(
            optimize_equilibrium(
                EquilibriumField(stronger.exact_frontier(query), config)
            ).final_state
        )
        movements.append(
            float(stronger_state @ target) > float(ordinary_state @ target)
        )

    relevant = rng.normal(size=(20, 384))
    relevant /= np.linalg.norm(relevant, axis=1, keepdims=True)
    irrelevant = rng.normal(size=(200, 384))
    irrelevant /= np.linalg.norm(irrelevant, axis=1, keepdims=True)
    base = SemanticFieldHierarchy.build(relevant, [{"priority": 1.0}] * len(relevant))
    expanded = SemanticFieldHierarchy.build(
        np.vstack([relevant, irrelevant]),
        [{"priority": 1.0}] * len(relevant) + [{"priority": 0.01}] * len(irrelevant),
    )
    base_state = np.asarray(
        optimize_equilibrium(
            EquilibriumField(base.exact_frontier(relevant[0]), config)
        ).final_state
    )
    expanded_state = np.asarray(
        optimize_equilibrium(
            EquilibriumField(expanded.exact_frontier(relevant[0]), config)
        ).final_state
    )
    return {
        "weight_monotonic_fraction": float(np.mean(movements)),
        "irrelevant_expansion_cosine_drift": 1.0 - float(base_state @ expanded_state),
    }


def _decision(
    rows: list[dict[str, Any]],
    scaling: dict[str, Any],
    controlled: dict[str, float],
) -> tuple[str, dict[str, Any]]:
    summary = _summary(rows)
    direct = [row for row in rows if row["method"] == "direct"]
    exact = [row for row in rows if row["method"] == "exact_equilibrium"]
    hierarchical = [row for row in rows if row["method"] == "hierarchical_equilibrium"]
    interval = _bootstrap(
        [row["recall_at_4"] for row in direct],
        [row["recall_at_4"] for row in exact],
    )
    worst_improvement = 1.0 - (
        summary["exact_equilibrium"]["worst_high_weight_residual"]
        / max(summary["barycenter"]["worst_high_weight_residual"], 1e-12)
    )
    average_ratio = summary["exact_equilibrium"]["average_weighted_residual"] / max(
        summary["barycenter"]["average_weighted_residual"], 1e-12
    )
    numerical_failures = sum(
        not row["unit_norm"]
        or row["final_energy"] > row["initial_energy"] + 1e-8
        or row["field_evaluations"] > 16
        for row in exact + hierarchical
    )
    gate = {
        "worst_residual_improvement": worst_improvement,
        "average_residual_ratio": average_ratio,
        "recall_improvement": (
            summary["exact_equilibrium"]["recall_at_4"]
            - summary["direct"]["recall_at_4"]
        ),
        "bootstrap_recall_difference_95pct": interval,
        "minimum_prompt_cosine": min(row["prompt_cosine"] for row in exact),
        "minimum_hierarchy_exact_cosine": min(
            row["exact_state_cosine"] for row in hierarchical
        ),
        "maximum_hierarchy_energy_error": max(
            row["relative_oracle_energy_error"] for row in hierarchical
        ),
        "mean_hierarchy_evidence_overlap": float(
            np.mean([row["exact_evidence_overlap"] for row in hierarchical])
        ),
        "numerical_failures": numerical_failures,
        "peak_rss_mb_10000": scaling["10000"]["peak_rss_mb"],
        "warm_optimization_ms_10000": scaling["10000"]["optimization_ms"],
        **controlled,
    }
    mechanical = numerical_failures == 0
    hierarchy_pass = (
        gate["minimum_hierarchy_exact_cosine"] >= 0.99
        and gate["maximum_hierarchy_energy_error"] <= 0.02
        and gate["mean_hierarchy_evidence_overlap"] >= 0.90
        and scaling["10000"]["represented_once"]
        and gate["peak_rss_mb_10000"] < 8192
        and gate["warm_optimization_ms_10000"] < 5000
    )
    equilibrium_pass = (
        worst_improvement >= 0.10
        and average_ratio <= 1.05
        and gate["recall_improvement"] >= 0.05
        and interval[0] > 0
        and gate["minimum_prompt_cosine"] >= 0.60
        and gate["weight_monotonic_fraction"] >= 0.95
        and gate["irrelevant_expansion_cosine_drift"] <= 0.05
    )
    if not mechanical:
        classification = "E-D"
    elif equilibrium_pass and not hierarchy_pass:
        classification = "E-C"
    elif equilibrium_pass and hierarchy_pass:
        classification = "E-A"
    else:
        classification = "E-B"
    return classification, {"summary": summary, "gate": gate}


def run(
    workspace: Path,
    dev_suite: Path,
    test_suite: Path,
    output: Path,
) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    workspace_config = load_workspace_config(workspace / "workspace.json")
    model = load_embedding_model(
        Path(workspace_config.embedding_model_path),
        resolve_device(workspace_config.device),
    )
    dev_paths = [dev_suite]
    dev = _encode(model, _load_development(dev_paths))
    dev_hierarchy = SemanticFieldHierarchy.build(
        dev["vectors"], [chunk.metadata for chunk in dev["chunks"]]
    )
    grid = _development_grid(dev, dev_hierarchy)
    selected_item = _select(grid)
    (output / "phase-1.2-dev-grid.json").write_text(
        json.dumps(grid, indent=2) + "\n", encoding="utf-8"
    )
    (output / "phase-1.2-selected-config.json").write_text(
        json.dumps(selected_item, indent=2) + "\n", encoding="utf-8"
    )

    # The held-out suite is intentionally not opened until selection is frozen.
    test = _encode(model, _load_held_out(test_suite))
    config = EquilibriumConfig(**selected_item["config"])
    hierarchy_started = time.perf_counter()
    hierarchy = SemanticFieldHierarchy.build(
        test["vectors"], [chunk.metadata for chunk in test["chunks"]]
    )
    hierarchy_build_ms = (time.perf_counter() - hierarchy_started) * 1000
    rows = _evaluate_test(test, hierarchy, config, workspace_config)
    scaling = _scale_checks(
        test["vectors"], [chunk.metadata for chunk in test["chunks"]], config
    )
    controlled = _controlled_checks(config)
    classification, decision = _decision(rows, scaling, controlled)
    corpus_hash = hashlib.sha256(
        "\n".join(chunk.model_dump_json() for chunk in test["chunks"]).encode()
    ).hexdigest()
    manifest = {
        "corpus_sha256": corpus_hash,
        "item_count": len(test["chunks"]),
        "node_count": len(hierarchy.nodes),
        "root_id": hierarchy.root_id,
        "branching_factor": hierarchy.branching_factor,
        "leaf_size": hierarchy.leaf_size,
        "build_ms": hierarchy_build_ms,
    }
    result = {
        "classification": classification,
        "case_count": len(test["cases"]),
        "model_id": workspace_config.embedding_model_id,
        "model_revision": workspace_config.embedding_revision,
        "dev_suite_sha256": [_sha256(path) for path in dev_paths],
        "test_suite_sha256": _sha256(test_suite),
        "selected_config": selected_item["config"],
        "hierarchy_manifest": manifest,
        "scaling": scaling,
        **decision,
        "rows": rows,
    }
    artifacts = {
        "phase-1.2-hierarchy-manifest.json": manifest,
        "phase-1.2-exact-oracle-comparison.json": {
            "rows": [row for row in rows if row["method"] == "hierarchical_equilibrium"]
        },
        "phase-1.2-scaling.json": scaling,
        "phase-1.2-test-results.json": result,
    }
    for name, payload in artifacts.items():
        (output / name).write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )
    _write_markdown(result, output / "phase-1.2-test-results.md")
    return result


def _write_markdown(result: dict[str, Any], path: Path) -> None:
    lines = [
        "# Phase 1.2 Held-Out Results",
        "",
        f"Classification: **{result['classification']}**",
        "",
        "| Method | Recall@4 | Precision@4 | Worst residual | Prompt cosine |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for method, summary in result["summary"].items():
        lines.append(
            f"| {method} | {summary['recall_at_4']:.3f} | "
            f"{summary['precision_at_4']:.3f} | "
            f"{summary['worst_high_weight_residual']:.3f} | "
            f"{summary['prompt_cosine']:.3f} |"
        )
    lines.extend(["", "## Gate", ""])
    lines.extend(f"- {key}: `{value}`" for key, value in result["gate"].items())
    lines.extend(
        [
            "",
            "The experiment measures weighted semantic compatibility. "
            "It does not establish logical truth or causal reasoning.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
