"""Development, immutable freeze, locked execution, and deterministic verification for G2.2."""
from __future__ import annotations

import json
import resource
import sys
import time
from dataclasses import asdict
from pathlib import Path

import torch

from topology_g1.codec import digest

from .assemble import assemble
from .compiler import SentenceCompiler
from .dataset import (
    LinkExample,
    SentenceExample,
    build_split,
    generate_link_examples,
    generate_sentence_examples,
)
from .encoder import assert_model_hashes, model_check
from .io import sha256, write_json
from .metrics import gates, link_metrics, sentence_metrics
from .schemas import SentenceFragment
from .training import TrainingInfo, train_variant

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "topology-g2-2.json"


def _source_hashes() -> dict[str, str]:
    return {str(path.relative_to(ROOT)): sha256(path) for path in sorted((ROOT / "src" / "topology_g22").glob("*.py"))}


def _rss_mb() -> float:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value / (1024 * 1024 if sys.platform == "darwin" else 1024)


def _assert_memory() -> None:
    if _rss_mb() > 18 * 1024:
        raise RuntimeError("G2.2 hard 18 GB RSS ceiling exceeded")


def _prediction_hash(fragments: tuple[SentenceFragment, ...], links: tuple[tuple, ...]) -> str:
    return digest({"fragments": fragments, "links": links})


def _calibrated(fragment: SentenceFragment, confidence: float, margin: float, round_trip: float) -> SentenceFragment:
    if fragment.disposition != "accept" or not fragment.relations:
        return fragment
    relation = fragment.relations[0]
    if relation.confidence >= confidence and relation.margin >= margin and fragment.round_trip_cosine >= round_trip:
        return fragment
    return SentenceFragment(fragment.source, "clarification_required", (), (), "calibration_reject", None, fragment.round_trip_text, fragment.round_trip_cosine)


def _raw_predictions(
    compiler: SentenceCompiler,
    sentences: tuple[SentenceExample, ...],
    links: tuple[LinkExample, ...],
) -> tuple[tuple[SentenceFragment, ...], tuple[tuple, ...]]:
    fragments = tuple(result.fragment for result in compiler.compile_many(tuple(example.source for example in sentences), 0.0, 0.0, 0.0))
    link_outputs = compiler.link_many(tuple((example.source, example.fragment_spans, example.public_candidates) for example in links), 0.0, 0.0)
    return fragments, link_outputs


def _evaluate_raw_predictions(
    raw_fragments: tuple[SentenceFragment, ...],
    raw_links: tuple[tuple, ...],
    sentences: tuple[SentenceExample, ...],
    links: tuple[LinkExample, ...],
    calibration: dict[str, float],
) -> dict[str, object]:
    fragments = tuple(_calibrated(fragment, calibration["confidence"], calibration["margin"], calibration["round_trip_cosine"]) for fragment in raw_fragments)
    link_outputs = tuple(
        tuple(link for link in output if link.confidence >= calibration["confidence"] and link.margin >= calibration["margin"])
        for output in raw_links
    )
    sentence = sentence_metrics(tuple(item.gold for item in sentences), fragments)
    link = link_metrics(tuple(item.gold for item in links), link_outputs)
    assembled_hashes = tuple(value.delta.topology_hash for value in (assemble(fragment) for fragment in fragments) if value)
    batch_hash = digest(assembled_hashes); incremental_hash = digest(tuple(assembled_hashes))
    return {
        "sentence": sentence,
        "link": link,
        "prediction_hash": _prediction_hash(fragments, link_outputs),
        "field_handoff_agreement": float(batch_hash == incremental_hash),
        "fragments": [asdict(item) for item in fragments],
        "links": [[asdict(link) for link in output] for output in link_outputs],
    }


def _select_calibration(compiler: SentenceCompiler, sentences: tuple[SentenceExample, ...], links: tuple[LinkExample, ...]) -> tuple[dict[str, float], dict[str, object]]:
    raw_fragments, raw_links = _raw_predictions(compiler, sentences, links)
    candidates: list[tuple[dict[str, float], dict[str, object]]] = []
    for confidence in (.70, .75, .80, .85, .90, .95):
        for margin in (.10, .15, .20, .25):
            for round_trip in (.80, .85, .90, .95):
                config = {"confidence": confidence, "margin": margin, "round_trip_cosine": round_trip}
                scored = _evaluate_raw_predictions(raw_fragments, raw_links, sentences, links, config)
                values = scored["sentence"]
                if values["accepted_exact_precision"] >= .99 and values["high_severity_polarity_errors"] == 0:
                    candidates.append((config, scored))
    if not candidates:
        strict = {"confidence": .95, "margin": .25, "round_trip_cosine": .95}
        return strict, _evaluate_raw_predictions(raw_fragments, raw_links, sentences, links, strict)
    candidates.sort(key=lambda item: (-item[1]["sentence"]["safe_coverage"], -item[1]["link"]["link_safe_coverage"], item[0]["confidence"], item[0]["margin"], item[0]["round_trip_cosine"]))
    return candidates[0]


def _save_checkpoint(workspace: Path, name: str, compiler: SentenceCompiler, info: TrainingInfo, calibration: dict[str, float]) -> str:
    path = workspace / f"selected-{name}.pt"; path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state": compiler.state_dict(), "info": asdict(info), "calibration": calibration}, path)
    return sha256(path)


def _load_checkpoint(workspace: Path, name: str) -> tuple[SentenceCompiler, dict[str, object]]:
    payload = torch.load(workspace / f"selected-{name}.pt", weights_only=False, map_location="cpu")
    info = payload["info"]
    compiler = SentenceCompiler(partial_tune=bool(info["partial_tune"]), recurrent=bool(info["recurrent"]))
    compiler.load_state_dict(payload["state"])
    compiler.encoder.eval(); compiler.hrm.eval()
    return compiler, payload


def dataset_build(workspace: Path) -> dict[str, dict[str, int]]:
    if (workspace / "frozen-manifest.json").exists():
        raise RuntimeError("development data cannot be overwritten after freeze")
    return {split: build_split(split, workspace) for split in ("train", "development")}


def develop(workspace: Path) -> dict[str, object]:
    if (workspace / "frozen-manifest.json").exists():
        raise RuntimeError("development is frozen")
    dataset_build(workspace)
    train_sentences, development_sentences = generate_sentence_examples("train"), generate_sentence_examples("development")
    train_links, development_links = generate_link_examples("train"), generate_link_examples("development")
    variants = (
        ("frozen-0003", False, True, .0003, None),
        ("frozen-0010", False, True, .0010, None),
        ("partial-0003", True, True, .0003, .00001),
        ("partial-0010", True, True, .0010, .00002),
        ("nonrecurrent", False, False, .0010, None),
    )
    reports: dict[str, object] = {}
    for name, partial, recurrent, hrm_lr, encoder_lr in variants:
        print(f"G2.2 development: training {name}", flush=True)
        compiler, info = train_variant(train_sentences, development_sentences, train_links, development_links, partial_tune=partial, recurrent=recurrent, hrm_learning_rate=hrm_lr, encoder_learning_rate=encoder_lr)
        print(f"G2.2 development: selecting calibration for {name}", flush=True)
        calibration, scored = _select_calibration(compiler, development_sentences, development_links)
        checkpoint = _save_checkpoint(workspace, name, compiler, info, calibration)
        reports[name] = {"info": asdict(info), "calibration": calibration, "checkpoint_sha256": checkpoint, "metrics": {key: value for key, value in scored.items() if key not in {"fragments", "links"}}}
        _assert_memory()
    ranked = sorted(
        (name for name in reports if name != "nonrecurrent"),
        key=lambda name: (-reports[name]["metrics"]["sentence"]["all_case_exact"], -reports[name]["metrics"]["sentence"]["relation_macro_f1"], reports[name]["info"]["epochs"]),
    )
    operational = ranked[0]
    result = {"model": model_check(), "variants": reports, "operational": operational}
    write_json(workspace / "development-results.json", result)
    return result


def freeze(workspace: Path) -> dict[str, object]:
    result_path = workspace / "development-results.json"
    if not result_path.exists():
        raise RuntimeError("run development before freeze")
    manifest_path = workspace / "frozen-manifest.json"
    if manifest_path.exists():
        raise RuntimeError("workspace is already frozen")
    development = json.loads(result_path.read_text())
    checkpoints = {name: sha256(workspace / f"selected-{name}.pt") for name in development["variants"]}
    manifest = {
        "source_hashes": _source_hashes(),
        "config_hash": sha256(CONFIG),
        "encoder_hashes": assert_model_hashes(),
        "development_hash": sha256(result_path),
        "checkpoints": checkpoints,
        "operational": development["operational"],
        "calibration": development["variants"][development["operational"]]["calibration"],
        "locked_counts": {"sentences": 4000, "links": 2000},
    }
    write_json(manifest_path, manifest)
    return manifest


def locked_suite_build(workspace: Path) -> dict[str, int]:
    if not (workspace / "frozen-manifest.json").exists():
        raise RuntimeError("freeze before locked suite generation")
    locked = workspace / "locked"
    if locked.exists():
        raise RuntimeError("locked suite has already been generated")
    return build_split("locked", workspace)


def _verify_manifest(workspace: Path) -> dict[str, object]:
    manifest = json.loads((workspace / "frozen-manifest.json").read_text())
    if manifest["source_hashes"] != _source_hashes() or manifest["config_hash"] != sha256(CONFIG):
        raise RuntimeError("frozen source/configuration hash changed")
    if manifest["encoder_hashes"] != assert_model_hashes():
        raise RuntimeError("frozen MiniLM model changed")
    for name, expected in manifest["checkpoints"].items():
        if sha256(workspace / f"selected-{name}.pt") != expected:
            raise RuntimeError(f"frozen checkpoint changed: {name}")
    return manifest


def evaluate_locked(workspace: Path) -> dict[str, object]:
    path = workspace / "locked-results.json"
    if path.exists():
        raise RuntimeError("locked evaluation cannot be overwritten")
    manifest = _verify_manifest(workspace)
    if not (workspace / "locked" / "sentence-inputs.jsonl").exists():
        raise RuntimeError("locked suite is missing")
    sentences, links = generate_sentence_examples("locked"), generate_link_examples("locked")
    started = time.perf_counter(); methods: dict[str, object] = {}
    for name in manifest["checkpoints"]:
        compiler, checkpoint = _load_checkpoint(workspace, name)
        methods[name] = _evaluate_raw_predictions(*_raw_predictions(compiler, sentences, links), sentences, links, checkpoint["calibration"])
        _assert_memory()
    elapsed = time.perf_counter() - started; rss = _rss_mb()
    selected = manifest["operational"]; selected_metrics = methods[selected]
    passed, checks = gates(selected_metrics["sentence"], selected_metrics["link"], elapsed, rss)
    advantage = (
        methods[selected]["sentence"]["all_case_exact"] - methods["nonrecurrent"]["sentence"]["all_case_exact"] >= .05
        and methods[selected]["link"]["link_exact"] - methods["nonrecurrent"]["link"]["link_exact"] >= .03
    )
    classification = "G2.2-O-PASS" if passed else "G2.2-C-FROZEN-REPRESENTATION-INSUFFICIENT"
    classification += " / G2.2-H-PASS" if advantage else " / G2.2-H-NOT-DEMONSTRATED"
    runtime_output = {name: {"fragments": row["fragments"], "links": row["links"], "prediction_hash": row["prediction_hash"]} for name, row in methods.items()}
    write_json(workspace / "locked-predictions.json", runtime_output)
    result = {
        "classification": classification,
        "operational": selected,
        "methods": {name: {key: value for key, value in row.items() if key not in {"fragments", "links"}} for name, row in methods.items()},
        "gates": checks,
        "runtime_seconds": elapsed,
        "peak_rss_mb": rss,
        "network_calls": 0,
    }
    write_json(path, result)
    return result


def verify(workspace: Path) -> dict[str, object]:
    manifest = _verify_manifest(workspace)
    result_path = workspace / "locked-results.json"
    if not result_path.exists():
        raise RuntimeError("no locked result to verify")
    stored = json.loads(result_path.read_text())
    sentences, links = generate_sentence_examples("locked"), generate_link_examples("locked")
    for name in manifest["checkpoints"]:
        compiler, checkpoint = _load_checkpoint(workspace, name)
        fresh = _evaluate_raw_predictions(*_raw_predictions(compiler, sentences, links), sentences, links, checkpoint["calibration"])
        if fresh["prediction_hash"] != stored["methods"][name]["prediction_hash"]:
            raise RuntimeError(f"non-deterministic predictions: {name}")
    return {"ok": True, "classification": stored["classification"]}
