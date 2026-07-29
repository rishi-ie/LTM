"""Fixed Phase 1 comparison of retrieval, mean shift, and latent optimization."""

import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from ltm_poc.config import load_workspace_config
from ltm_poc.devices import resolve_device
from ltm_poc.experiments.common import chunks_from_documents, quality
from ltm_poc.field import LatentField
from ltm_poc.models import load_embedding_model
from ltm_poc.optimize import mean_shift, optimize
from ltm_poc.retrieve import retrieve


def classify(summary: dict[str, dict[str, float]]) -> str:
    direct, mean, latent = summary["direct"], summary["mean_shift"], summary["latent"]
    improvement = latent["recall_at_4"] - direct["recall_at_4"]
    precision_loss = direct["precision_at_4"] - latent["precision_at_4"]
    dominated = (
        mean["recall_at_4"] >= latent["recall_at_4"]
        and mean["latency_ms"] <= latent["latency_ms"]
    )
    return (
        "A" if improvement >= 0.05 and precision_loss <= 0.05 and not dominated else "B"
    )


def run(workspace: Path, suite_path: Path) -> dict[str, Any]:
    config = load_workspace_config(workspace / "workspace.json")
    device = resolve_device(config.device)
    model = load_embedding_model(Path(config.embedding_model_path), device)
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
    vectors = np.asarray(encoded[: len(chunks)], dtype=np.float32)
    local = config.model_copy(
        update={
            "active_candidates": min(config.active_candidates, len(chunks)),
            "evidence_limit": min(4, len(chunks)),
        }
    )
    rows: list[dict[str, Any]] = []
    for query_index, (scenario, offset, query_text) in enumerate(queries):
        query = np.asarray(encoded[len(chunks) + query_index], dtype=np.float32)
        gold = set(scenario["gold"])
        field = LatentField.construct(query, vectors, chunks, local)
        methods: dict[str, tuple[np.ndarray, int]] = {"direct": (query, 0)}
        start = time.perf_counter()
        shifted = mean_shift(field)
        mean_ms = (time.perf_counter() - start) * 1000
        start = time.perf_counter()
        result = optimize(field, local)
        latent_ms = (time.perf_counter() - start) * 1000
        methods["mean_shift"] = (shifted.astype(np.float32), 8)
        methods["latent"] = (
            np.asarray(result.final_state, dtype=np.float32),
            result.field_evaluations,
        )
        for name, (state, evaluations) in methods.items():
            started = time.perf_counter()
            _, evidence = retrieve(state, vectors, chunks, local.evidence_limit)
            latency = (time.perf_counter() - started) * 1000
            if name == "mean_shift":
                latency += mean_ms
            if name == "latent":
                latency += latent_ms
            ids = [item.chunk_id for item in evidence]
            recall, precision = quality(ids, gold)
            rows.append(
                {
                    "case_id": f"{scenario['id']}-{offset + 1:02d}",
                    "method": name,
                    "recall_at_4": recall,
                    "precision_at_4": precision,
                    "ids": ids,
                    "latency_ms": latency,
                    "field_evaluations": evaluations,
                    "energy_decreased": name != "latent"
                    or result.final_energy <= result.initial_energy,
                }
            )
    summary = {
        name: {
            metric: float(
                np.mean([row[metric] for row in rows if row["method"] == name])
            )
            for metric in (
                "recall_at_4",
                "precision_at_4",
                "latency_ms",
                "field_evaluations",
            )
        }
        for name in ("direct", "mean_shift", "latent")
    }
    return {
        "case_count": 50,
        "summary": summary,
        "classification": classify(summary),
        "rows": rows,
    }


def write_report(result: dict[str, Any], output: Path) -> tuple[Path, Path]:
    output.mkdir(parents=True, exist_ok=True)
    json_path, markdown_path = (
        output / "phase-1-results.json",
        output / "phase-1-results.md",
    )
    json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Phase 1 Experiment Results",
        "",
        f"Cases: {result['case_count']}",
        f"Classification: Result {result['classification']}",
        "",
        "| Method | Recall@4 | Precision@4 | Mean latency ms | Field evaluations |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name, metrics in result["summary"].items():
        quality_values = (
            f"{metrics['recall_at_4']:.3f} | {metrics['precision_at_4']:.3f}"
        )
        lines.append(
            f"| {name} | {quality_values} | "
            f"{metrics['latency_ms']:.3f} | {metrics['field_evaluations']:.2f} |"
        )
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, markdown_path
