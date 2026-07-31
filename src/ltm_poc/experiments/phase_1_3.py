"""Phase 1.3: semantic LTM versus deterministic traditional RAG."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

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
from ltm_poc.experiments.multi_state import (
    LatentSetField,
    SetOptimizerConfig,
    initialize_states,
    optimize_set,
    resolve_set_evidence,
)
from ltm_poc.experiments.rag import BM25Index, bm25_retrieve, hybrid_retrieve
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
    tokens = max(1, len(text.split()))
    return ChunkRecord(
        chunk_id=chunk_id,
        record_id=chunk_id,
        source_path=chunk_id,
        source_kind="text",
        text=text,
        char_start=0,
        char_end=len(text),
        token_start=0,
        token_end=tokens,
        token_count=tokens,
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
        metadata=metadata or {},
    )


def load_suite(path: Path) -> dict[str, Any]:
    """Load either the Phase 1.3 schema or the earlier scenario fixtures."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "domains" in payload:
        chunks: dict[str, dict[str, Any]] = {}
        cases: list[dict[str, Any]] = []
        for domain in payload["domains"]:
            for chunk_id, value in domain["documents"].items():
                chunks[chunk_id] = value if isinstance(value, dict) else {"text": value}
            for case in domain["cases"]:
                cases.append({**case, "domain": case.get("domain", domain["id"])})
        return {
            "chunks": [
                _chunk(k, v["text"], v.get("metadata"))
                for k, v in sorted(chunks.items())
            ],
            "cases": cases,
        }
    if isinstance(payload, dict) and "cases" in payload:
        documents = payload.get("documents", {})
        return {
            "chunks": [
                _chunk(k, v["text"] if isinstance(v, dict) else v)
                for k, v in sorted(documents.items())
            ],
            "cases": payload["cases"],
        }
    documents: dict[str, str] = {}
    cases: list[dict[str, Any]] = []
    for scenario in payload:
        documents.update(scenario["documents"])
        for offset, query in enumerate(
            scenario.get("queries", [scenario.get("query", "")])
        ):
            cases.append(
                {
                    "id": f"{scenario['id']}-{offset + 1:02d}",
                    "domain": scenario["id"],
                    "category": scenario.get("category", "legacy"),
                    "query": query,
                    "gold": list(
                        scenario.get("gold", scenario.get("gold_evidence", []))
                    ),
                    "answer": scenario.get("answer", ""),
                }
            )
    return {
        "chunks": [_chunk(k, v) for k, v in sorted(documents.items())],
        "cases": cases,
    }


def _encode(model: Any, prepared: dict[str, Any]) -> dict[str, Any]:
    chunks, cases = prepared["chunks"], prepared["cases"]
    values = model.encode(
        [item.text for item in chunks] + [case["query"] for case in cases],
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return {
        **prepared,
        "vectors": np.asarray(values[: len(chunks)], dtype=np.float32),
        "queries": np.asarray(values[len(chunks) :], dtype=np.float32),
    }


def _gold(case: dict[str, Any]) -> set[str]:
    return set(
        case.get("gold", case.get("gold_evidence", case.get("supporting_facts", [])))
    )


def _row(
    case: dict[str, Any],
    method: str,
    evidence: list[Any],
    latency_ms: float,
    **extra: Any,
) -> dict[str, Any]:
    ids = [
        item.chunk_id if hasattr(item, "chunk_id") else item["chunk_id"]
        for item in evidence
    ]
    gold = _gold(case)
    recall, precision = (quality(ids, gold) if gold else (0.0, 0.0))
    return {
        "case_id": case["id"],
        "domain": case.get("domain", "unknown"),
        "category": case.get("category", "unknown"),
        "method": method,
        "ids": ids,
        "recall_at_4": recall,
        "precision_at_4": precision,
        "latency_ms": latency_ms,
        **extra,
    }


def _summary(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    methods = sorted({row["method"] for row in rows})
    metrics = ("recall_at_4", "precision_at_4", "latency_ms")
    return {
        method: {
            metric: float(
                np.mean([row[metric] for row in rows if row["method"] == method])
            )
            for metric in metrics
        }
        for method in methods
    }


def _bootstrap_difference(
    left: list[float], right: list[float], samples: int = 2000
) -> list[float]:
    difference = np.asarray(left, dtype=np.float64) - np.asarray(
        right, dtype=np.float64
    )
    if not len(difference):
        return [0.0, 0.0]
    rng = np.random.default_rng(1729)
    means = [
        float(np.mean(rng.choice(difference, len(difference), replace=True)))
        for _ in range(samples)
    ]
    return [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))]


def evaluate_suite(
    prepared: dict[str, Any], workspace_config: Any, include_answers: bool = False
) -> dict[str, Any]:
    chunks, vectors, queries = (
        prepared["chunks"],
        prepared["vectors"],
        prepared["queries"],
    )
    limit = min(4, len(chunks))
    local = workspace_config.model_copy(
        update={
            "active_candidates": min(workspace_config.active_candidates, len(chunks)),
            "evidence_limit": limit,
        }
    )
    bm25 = BM25Index.build(chunks)
    hierarchy = SemanticFieldHierarchy.build(
        vectors.astype(np.float64), [dict(chunk.metadata) for chunk in chunks]
    )
    set_config = SetOptimizerConfig()
    equilibrium_config = EquilibriumConfig(query_anchor=0.5, max_weight=2.0)
    rows: list[dict[str, Any]] = []
    for case, query in zip(prepared["cases"], queries):
        started = time.perf_counter()
        dense_scores = vectors @ query
        dense_indices = sorted(
            range(len(chunks)),
            key=lambda i: (-float(dense_scores[i]), chunks[i].chunk_id),
        )[:limit]
        dense = retrieve(query, vectors, chunks, limit)[1]
        rows.append(_row(case, "dense", dense, (time.perf_counter() - started) * 1000))
        started = time.perf_counter()
        lexical = bm25_retrieve(case["query"], chunks, bm25, limit)
        rows.append(_row(case, "bm25", lexical, (time.perf_counter() - started) * 1000))
        started = time.perf_counter()
        hybrid = hybrid_retrieve(case["query"], query, vectors, chunks, bm25, limit)
        rows.append(
            _row(case, "hybrid", hybrid, (time.perf_counter() - started) * 1000)
        )
        field = LatentField.construct(query, vectors, chunks, local)
        started = time.perf_counter()
        latent_result = optimize(field, local)
        latent = retrieve(
            np.asarray(latent_result.final_state), vectors, chunks, limit
        )[1]
        rows.append(
            _row(
                case,
                "single_latent",
                latent,
                (time.perf_counter() - started) * 1000,
                field_evaluations=latent_result.field_evaluations,
                energy_decreased=latent_result.final_energy
                <= latent_result.initial_energy + 1e-8,
            )
        )
        started = time.perf_counter()
        states = initialize_states(
            field, [chunks[i] for i in range(len(field.evidence))], set_config
        )
        set_result = optimize_set(
            LatentSetField(
                field, set_config.diversity_weight, set_config.similarity_cap
            ),
            states,
            set_config,
        )
        multi = resolve_set_evidence(field, np.asarray(set_result.final_states), limit)
        rows.append(
            _row(
                case,
                "multi_state",
                multi,
                (time.perf_counter() - started) * 1000,
                set_evaluations=set_result.set_evaluations,
            )
        )
        started = time.perf_counter()
        exact_field = EquilibriumField(
            hierarchy.exact_frontier(query), equilibrium_config
        )
        exact_result = optimize_equilibrium(exact_field)
        exact_bundle = build_evidence_bundle(exact_field, exact_result, chunks)
        exact = [item for item in exact_bundle["evidence"][:limit]]
        rows.append(
            _row(
                case,
                "exact_equilibrium",
                exact,
                (time.perf_counter() - started) * 1000,
                field_evaluations=exact_result.field_evaluations,
                energy_decreased=exact_result.final_energy
                <= exact_result.initial_energy + 1e-8,
            )
        )
        started = time.perf_counter()
        hierarchical_field = EquilibriumField(
            hierarchy.compile_frontier(query), equilibrium_config
        )
        hierarchical_result = optimize_equilibrium(hierarchical_field)
        hierarchical_bundle = build_evidence_bundle(
            hierarchical_field, hierarchical_result, chunks
        )
        hierarchical = hierarchical_bundle["evidence"][:limit]
        rows.append(
            _row(
                case,
                "hierarchical_equilibrium",
                hierarchical,
                (time.perf_counter() - started) * 1000,
                field_evaluations=hierarchical_result.field_evaluations,
                energy_decreased=hierarchical_result.final_energy
                <= hierarchical_result.initial_energy + 1e-8,
            )
        )
        rows.append(
            _row(case, "prompt_state", retrieve(query, vectors, chunks, limit)[1], 0.0)
        )
        _ = dense_indices  # retains explicit dense ordering for reproducibility audits
    summary = _summary(rows)
    direct = [row["recall_at_4"] for row in rows if row["method"] == "dense"]
    hybrid = [row["recall_at_4"] for row in rows if row["method"] == "hybrid"]
    single = [row["recall_at_4"] for row in rows if row["method"] == "single_latent"]
    return {
        "case_count": len(prepared["cases"]),
        "summary": summary,
        "rows": rows,
        "bootstrap_single_vs_hybrid": _bootstrap_difference(single, hybrid),
        "bootstrap_single_vs_dense": _bootstrap_difference(single, direct),
        "include_answers": include_answers,
    }


def run(workspace: Path, suite_path: Path) -> dict[str, Any]:
    config = load_workspace_config(workspace / "workspace.json")
    model = load_embedding_model(
        Path(config.embedding_model_path), resolve_device(config.device)
    )
    prepared = _encode(model, load_suite(suite_path))
    result = evaluate_suite(prepared, config)
    result["suite_sha256"] = _sha256(suite_path)
    result["embedding_model"] = {
        "id": config.embedding_model_id,
        "revision": config.embedding_revision,
    }
    return result


def write_report(result: dict[str, Any], output: Path) -> tuple[Path, Path]:
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "phase-1.3-summary.json"
    markdown_path = output / "phase-1.3-results.md"
    json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Phase 1.3 Results",
        "",
        f"Cases: {result['case_count']}",
        "",
        "| Method | Recall@4 | Precision@4 | Latency ms |",
        "| --- | ---: | ---: | ---: |",
    ]
    for method, metrics in result["summary"].items():
        lines.append(
            "| {method} | {recall:.3f} | {precision:.3f} | {latency:.3f} |".format(
                method=method,
                recall=metrics["recall_at_4"],
                precision=metrics["precision_at_4"],
                latency=metrics["latency_ms"],
            )
        )
    lines.extend(
        [
            "",
            "Single latent vs hybrid bootstrap 95% CI: "
            f"{result['bootstrap_single_vs_hybrid']}",
        ]
    )
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, markdown_path
