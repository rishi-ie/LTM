"""Small command-line surface; commands are added as their components exist."""

import argparse
import json
import resource
import time
import uuid
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from ltm_poc.chunk import chunk_records
from ltm_poc.config import (
    WorkspaceConfig,
    load_workspace_config,
    write_workspace_config,
)
from ltm_poc.decode import decode
from ltm_poc.devices import device_report
from ltm_poc.embed import embed_chunks
from ltm_poc.experiments.phase_1 import run as run_evaluation
from ltm_poc.experiments.phase_1 import write_report
from ltm_poc.experiments.phase_1_1 import run as run_set_evaluation
from ltm_poc.experiments.phase_1_2 import run as run_equilibrium_evaluation
from ltm_poc.experiments.phase_1_3 import run as run_rag_evaluation
from ltm_poc.experiments.phase_1_3 import write_report as write_rag_report
from ltm_poc.field import LatentField
from ltm_poc.ingest import ingest
from ltm_poc.models import (
    DECODER_MODEL,
    EMBEDDING_MODEL,
    download_models,
    load_decoder,
    load_embedding_model,
    smoke_models,
)
from ltm_poc.optimize import optimize
from ltm_poc.retrieve import retrieve
from ltm_poc.schemas import QueryRun
from ltm_poc.store import CorpusStore


def _workspace_config(workspace: Path) -> WorkspaceConfig:
    return load_workspace_config(workspace / "workspace.json")


def _peak_rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)


def _init(workspace: Path, model_dir: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    write_workspace_config(
        workspace / "workspace.json",
        WorkspaceConfig(
            embedding_model_path=str((model_dir / EMBEDDING_MODEL.directory).resolve()),
            embedding_model_id=EMBEDDING_MODEL.repo_id,
            embedding_revision=EMBEDDING_MODEL.revision,
            decoder_model_path=str((model_dir / DECODER_MODEL.directory).resolve()),
            decoder_model_id=DECODER_MODEL.repo_id,
            decoder_revision=DECODER_MODEL.revision,
        ),
    )


def _ingest(workspace: Path, source: Path) -> dict[str, int]:
    config = _workspace_config(workspace)
    device = device_report()["auto_device"]
    result = ingest(source)
    embedder = load_embedding_model(Path(config.embedding_model_path), device)
    chunks = chunk_records(result.records, embedder.tokenizer, config)
    vectors = embed_chunks(chunks, embedder, config.embedding_batch_size)
    CorpusStore(workspace / "corpus").write(chunks, vectors, config)
    return {
        "records": len(result.records),
        "chunks": len(chunks),
        "skipped": len(result.skipped_files),
    }


def _ask(workspace: Path, prompt: str) -> QueryRun:
    started = time.perf_counter()
    config = _workspace_config(workspace)
    device = device_report()["auto_device"]
    chunks, vectors, manifest = CorpusStore(workspace / "corpus").read()
    embedder = load_embedding_model(Path(config.embedding_model_path), device)
    query = embedder.encode([prompt], convert_to_numpy=True, normalize_embeddings=True)[
        0
    ]
    _, initial = retrieve(query, vectors, chunks, config.evidence_limit)
    field = LatentField.construct(query, vectors, chunks, config)
    optimization = optimize(field, config)
    state = np.asarray(optimization.final_state, dtype=np.float32)
    _, final = retrieve(state, vectors, chunks, config.evidence_limit)
    tokenizer, decoder = load_decoder(Path(config.decoder_model_path), device)
    answer = decode(prompt, final, tokenizer, decoder, device, config)
    run = QueryRun(
        run_id=str(uuid.uuid4()),
        prompt=prompt,
        corpus_id=manifest.corpus_id,
        started_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        initial_evidence=initial,
        optimization=optimization,
        final_evidence=final,
        answer=answer,
        timings_ms={"total": (time.perf_counter() - started) * 1000},
        peak_rss_mb=_peak_rss_mb(),
    )
    with (workspace / "queries.jsonl").open("a", encoding="utf-8") as log:
        log.write(run.model_dump_json() + "\n")
    return run


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ltm-poc",
        description="Latent Topology Models Phase 1 semantic-field POC.",
    )
    subcommands = parser.add_subparsers(dest="command")
    doctor = subcommands.add_parser("doctor", help="report local device capability")
    doctor.add_argument("--json", action="store_true", help="emit JSON")
    doctor.add_argument(
        "--model-dir", type=Path, help="locally downloaded model directory"
    )
    models = subcommands.add_parser("models", help="manage pinned local models")
    model_commands = models.add_subparsers(dest="model_command", required=True)
    download = model_commands.add_parser(
        "download", help="download pinned model revisions"
    )
    download.add_argument("--model-dir", type=Path, required=True)
    init = subcommands.add_parser("init", help="create a local workspace")
    init.add_argument("--workspace", type=Path, required=True)
    init.add_argument("--model-dir", type=Path, default=Path(".models"))
    ingest_command = subcommands.add_parser(
        "ingest", help="compile local text into a corpus"
    )
    ingest_command.add_argument("--workspace", type=Path, required=True)
    ingest_command.add_argument("--source", type=Path, required=True)
    ask = subcommands.add_parser("ask", help="answer from an existing local corpus")
    ask.add_argument("--workspace", type=Path, required=True)
    ask.add_argument("prompt")
    evaluate = subcommands.add_parser("evaluate", help="run the fixed Phase 1 suite")
    evaluate.add_argument("--workspace", type=Path, required=True)
    evaluate.add_argument("--suite", type=Path, required=True)
    evaluate.add_argument("--output", type=Path, default=Path("results"))
    evaluate_set = subcommands.add_parser(
        "evaluate-set", help="run the Phase 1.1 multi-state experiment"
    )
    evaluate_set.add_argument("--workspace", type=Path, required=True)
    evaluate_set.add_argument("--dev-suite", type=Path, required=True)
    evaluate_set.add_argument("--test-suite", type=Path, required=True)
    evaluate_set.add_argument("--output", type=Path, required=True)
    evaluate_equilibrium = subcommands.add_parser(
        "evaluate-equilibrium", help="run the Phase 1.2 equilibrium experiment"
    )
    evaluate_equilibrium.add_argument("--workspace", type=Path, required=True)
    evaluate_equilibrium.add_argument("--dev-suite", type=Path, required=True)
    evaluate_equilibrium.add_argument("--test-suite", type=Path, required=True)
    evaluate_equilibrium.add_argument("--output", type=Path, required=True)
    evaluate_rag = subcommands.add_parser(
        "evaluate-rag", help="compare semantic LTM with deterministic RAG baselines"
    )
    evaluate_rag.add_argument("--workspace", type=Path, required=True)
    evaluate_rag.add_argument("--controlled-suite", type=Path, required=True)
    evaluate_rag.add_argument("--hotpot-suite", type=Path)
    evaluate_rag.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    if args.command == "doctor":
        report = device_report()
        if args.model_dir:
            report["model_smoke"] = smoke_models(args.model_dir, report["auto_device"])
        print(json.dumps(report, sort_keys=True) if args.json else report)
    if args.command == "models" and args.model_command == "download":
        print(json.dumps(download_models(args.model_dir), sort_keys=True))
    if args.command == "init":
        _init(args.workspace, args.model_dir)
    if args.command == "ingest":
        print(json.dumps(_ingest(args.workspace, args.source), sort_keys=True))
    if args.command == "ask":
        print(_ask(args.workspace, args.prompt).model_dump_json(indent=2))
    if args.command == "evaluate":
        result = run_evaluation(args.workspace, args.suite)
        json_path, markdown_path = write_report(result, args.output)
        print(
            json.dumps(
                {
                    "classification": result["classification"],
                    "json": str(json_path),
                    "markdown": str(markdown_path),
                },
                sort_keys=True,
            )
        )
    if args.command == "evaluate-set":
        result = run_set_evaluation(
            args.workspace, args.dev_suite, args.test_suite, args.output
        )
        print(
            json.dumps(
                {
                    "classification": result["classification"],
                    "results": str(args.output / "phase-1.1-test-results.json"),
                },
                sort_keys=True,
            )
        )
    if args.command == "evaluate-equilibrium":
        result = run_equilibrium_evaluation(
            args.workspace, args.dev_suite, args.test_suite, args.output
        )
        print(
            json.dumps(
                {
                    "classification": result["classification"],
                    "results": str(args.output / "phase-1.2-test-results.json"),
                },
                sort_keys=True,
            )
        )
    if args.command == "evaluate-rag":
        suites = [args.controlled_suite] + (
            [args.hotpot_suite] if args.hotpot_suite else []
        )
        combined: dict[str, object] = {"suites": {}}
        for suite in suites:
            result = run_rag_evaluation(args.workspace, suite)
            suite_result = args.output / suite.stem
            json_path, markdown_path = write_rag_report(result, suite_result)
            combined["suites"][suite.stem] = {
                "summary": result["summary"],
                "json": str(json_path),
                "markdown": str(markdown_path),
            }
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "phase-1.3-summary.json").write_text(
            json.dumps(combined, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(combined, sort_keys=True))
    return 0
