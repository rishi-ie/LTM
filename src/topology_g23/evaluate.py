from __future__ import annotations

import json
import resource
import sys
import time
from dataclasses import asdict
from pathlib import Path

import torch

from topology_g1.codec import digest

from .calibration import Calibration, calibrate, calibration_json
from .compiler import SentenceTopologyCompiler
from .dataset import build_split, generate_link_examples, generate_sentence_examples
from .diagnostics import run_diagnostics
from .encoder import assert_model_hashes, model_check
from .metrics import gates, link_metrics, sentence_metrics
from .runstate import atomic_json, begin_stage, checkpoint_stage, file_hash
from .training import train_variant

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "topology-g2-3.json"
VARIANTS = (("hierarchical", True), ("nonrecurrent", False))


def write_json(path: Path, value: object) -> None:
    atomic_json(path, value)


def rss_mb() -> float:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value / (1024 * 1024 if sys.platform == "darwin" else 1024)


def _source_hashes() -> dict[str, str]:
    return {
        str(path.relative_to(ROOT)): file_hash(path)
        for path in sorted((ROOT / "src" / "topology_g23").glob("*.py"))
    }


def _inputs_hashes() -> dict[str, str]:
    return {**_source_hashes(), "config": file_hash(CONFIG), **{f"model:{key}": value for key, value in assert_model_hashes().items()}}


def _json_prediction(results) -> list[dict[str, object]]:
    return [
        {
            "source_id": result.source_id,
            "disposition": result.disposition,
            "failure_codes": result.failure_codes,
            "accepted": result.accepted_ir is not None,
            "topology_hash": result.accepted_ir.topology_hash if result.accepted_ir else None,
            "hypotheses": [asdict(item) for item in result.hypotheses],
        }
        for result in results
    ]


def _predict(model: SentenceTopologyCompiler, examples, confidence: float, margin: float, chunk: int = 16):
    outputs = []
    for start in range(0, len(examples), chunk):
        group = tuple(item.source for item in examples[start : start + chunk])
        outputs.extend(model.forward(group, confidence=confidence, margin=margin))
    return tuple(outputs)


def _prediction_shards(
    workspace: Path,
    variant: str,
    name: str,
    factory,
    length: int,
    chunk: int,
):
    output = []
    root = workspace / "locked-shards" / variant / name
    for start in range(0, length, chunk):
        path = root / f"{start:05d}.pt"
        if path.exists():
            value = torch.load(path, weights_only=False, map_location="cpu")
        else:
            value = factory(start, min(length, start + chunk))
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(".tmp")
            torch.save(value, temporary)
            temporary.replace(path)
        output.extend(value)
    return tuple(output)


def _development_partitions(items):
    midpoint = len(items) // 2
    return tuple(items[:midpoint]), tuple(items[midpoint:])


def _save_checkpoint(workspace: Path, name: str, model: SentenceTopologyCompiler, info) -> Path:
    path = workspace / f"{name}-checkpoint.pt"
    temporary = path.with_suffix(".tmp")
    torch.save({"state": model.state_dict(), "recurrent": model.recurrent, "info": asdict(info)}, temporary)
    temporary.replace(path)
    return path


def _load(workspace: Path, name: str) -> SentenceTopologyCompiler:
    payload = torch.load(workspace / f"{name}-checkpoint.pt", weights_only=False, map_location="cpu")
    model = SentenceTopologyCompiler(recurrent=bool(payload["recurrent"]))
    model.load_state_dict(payload["state"])
    model.eval()
    return model


def dataset_build(workspace: Path) -> dict[str, object]:
    if (workspace / "frozen-manifest.json").exists():
        raise RuntimeError("development is frozen")
    return {split: build_split(split, workspace) for split in ("train", "development")}


def develop(workspace: Path) -> dict[str, object]:
    if (workspace / "frozen-manifest.json").exists():
        raise RuntimeError("development is frozen")
    inputs = _inputs_hashes()
    stage = begin_stage(workspace, "development", inputs, "g2-3-r1")
    result_path = workspace / "development-results.json"
    if stage.status == "completed" and result_path.exists():
        return json.loads(result_path.read_text(encoding="utf-8"))
    dataset_build(workspace)
    train_sentences = generate_sentence_examples("train")
    development_sentences = generate_sentence_examples("development")
    train_links = generate_link_examples("train")
    development_links = generate_link_examples("development")
    selection_sentences, calibration_sentences = _development_partitions(development_sentences)
    selection_links, _calibration_links = _development_partitions(development_links)
    reports: dict[str, object] = {}
    candidate_records = []
    for name, recurrent in VARIANTS:
        print(f"G2.3 development training {name}", flush=True)
        model, info = train_variant(
            train_sentences,
            selection_sentences,
            recurrent=recurrent,
            workspace=workspace,
            variant=name,
            link_train=train_links,
        )
        checkpoint = _save_checkpoint(workspace, name, model, info)
        raw_calibration = _predict(model, calibration_sentences, 0.0, 0.0)
        calibration = calibrate(calibration_sentences, raw_calibration)
        selected_outputs = _predict(model, selection_sentences, calibration.graph_confidence, calibration.graph_margin)
        selected_links = tuple(
            model.link(example.source, example.fragment_spans, example.public_candidates, calibration.link_confidence, calibration.link_margin)
            for example in selection_links
        )
        diagnostic = run_diagnostics(model, selection_sentences, selection_links, calibration.graph_confidence, calibration.graph_margin)
        sentence = sentence_metrics(selection_sentences, selected_outputs)
        link = link_metrics(selection_links, selected_links)
        reports[name] = {
            "info": asdict(info),
            "checkpoint": str(checkpoint),
            "checkpoint_hash": file_hash(checkpoint),
            "calibration": calibration_json(calibration),
            "selection_sentence": sentence,
            "selection_link": link,
            "diagnostic": diagnostic,
        }
        candidate_records.append((name, sentence, link, calibration))
    operational, _sentence, _link, calibration = max(
        candidate_records,
        key=lambda item: (
            item[1]["accepted_exact_precision"],
            item[1]["safe_coverage"],
            item[1]["all_case_exact"],
            item[1]["relation_role_exactness"],
            item[2]["link_exact"],
            -item[3].graph_confidence,
        ),
    )
    write_json(workspace / "selected-operational.json", {"method": operational, "calibration": calibration_json(calibration)})
    result = {
        "model": model_check(),
        "variants": reports,
        "operational": operational,
        "calibration": calibration_json(calibration),
    }
    write_json(result_path, result)
    checkpoint_stage(
        workspace,
        stage,
        status="completed",
        artifacts={"development_results": file_hash(result_path), "operational": operational},
    )
    return result


def audit_development(workspace: Path) -> dict[str, object]:
    """Rescore existing development checkpoints with semantic metric version 2.

    This is deliberately an audit artifact rather than a second development
    result.  It preserves the original interrupted prototype's outputs while
    exposing raw diagnostics before fail-closed calibration suppresses every
    candidate.
    """
    if not (workspace / "development-results.json").exists():
        raise RuntimeError("development checkpoints are required before audit")
    sentences = generate_sentence_examples("development")
    links = generate_link_examples("development")
    selection_sentences, calibration_sentences = _development_partitions(sentences)
    selection_links, _calibration_links = _development_partitions(links)
    variants: dict[str, object] = {}
    for name, _recurrent in VARIANTS:
        model = _load(workspace, name)
        with torch.no_grad():
            raw_calibration = _predict(model, calibration_sentences, 0.0, 0.0)
            raw_selection = _predict(model, selection_sentences, 0.0, 0.0)
            calibration = calibrate(calibration_sentences, raw_calibration)
            calibrated_selection = _predict(
                model,
                selection_sentences,
                calibration.graph_confidence,
                calibration.graph_margin,
            )
            raw_links = tuple(
                model.link(item.source, item.fragment_spans, item.public_candidates, 0.0, 0.0)
                for item in selection_links
            )
            diagnostics = run_diagnostics(model, selection_sentences, selection_links, 0.0, 0.0)
        variants[name] = {
            "raw_selection_sentence": sentence_metrics(selection_sentences, raw_selection),
            "raw_selection_link": link_metrics(selection_links, raw_links),
            "calibration": calibration_json(calibration),
            "calibrated_selection_sentence": sentence_metrics(selection_sentences, calibrated_selection),
            "diagnostics_raw": diagnostics,
            "checkpoint_hash": file_hash(workspace / f"{name}-checkpoint.pt"),
        }
    result = {
        "metric_version": 2,
        "source_hashes": _source_hashes(),
        "config_hash": file_hash(CONFIG),
        "workspace": str(workspace),
        "variants": variants,
        "boundary": "development audit only; no locked classification",
    }
    write_json(workspace / "diagnostic-audit-v2.json", result)
    return result


def freeze(workspace: Path) -> dict[str, object]:
    if (workspace / "frozen-manifest.json").exists():
        raise RuntimeError("already frozen")
    result_path = workspace / "development-results.json"
    selection_path = workspace / "selected-operational.json"
    if not result_path.exists() or not selection_path.exists():
        raise RuntimeError("complete development before freeze")
    manifest = {
        "source_hashes": _source_hashes(),
        "config_hash": file_hash(CONFIG),
        "model_hashes": assert_model_hashes(),
        "development_hash": file_hash(result_path),
        "selection_hash": file_hash(selection_path),
        "checkpoints": {name: file_hash(workspace / f"{name}-checkpoint.pt") for name, _ in VARIANTS},
        "operational": json.loads(selection_path.read_text(encoding="utf-8"))["method"],
        "locked_counts": {"sentences": 4000, "links": 2000},
    }
    write_json(workspace / "frozen-manifest.json", manifest)
    return manifest


def locked_suite_build(workspace: Path) -> dict[str, object]:
    if not (workspace / "frozen-manifest.json").exists():
        raise RuntimeError("freeze before locked generation")
    if (workspace / "locked").exists():
        raise RuntimeError("locked suite already exists")
    return build_split("locked", workspace)


def _verify_manifest(workspace: Path) -> dict[str, object]:
    manifest = json.loads((workspace / "frozen-manifest.json").read_text(encoding="utf-8"))
    if manifest["source_hashes"] != _source_hashes() or manifest["config_hash"] != file_hash(CONFIG):
        raise RuntimeError("frozen source or configuration hash changed")
    if manifest["model_hashes"] != assert_model_hashes():
        raise RuntimeError("frozen model hash changed")
    for name, value in manifest["checkpoints"].items():
        if file_hash(workspace / f"{name}-checkpoint.pt") != value:
            raise RuntimeError(f"checkpoint changed: {name}")
    return manifest


def _calibration(workspace: Path) -> Calibration:
    payload = json.loads((workspace / "selected-operational.json").read_text(encoding="utf-8"))["calibration"]
    return Calibration(**payload)


def evaluate_locked(workspace: Path) -> dict[str, object]:
    result_path = workspace / "locked-results.json"
    if result_path.exists():
        raise RuntimeError("locked evaluation cannot be overwritten")
    manifest = _verify_manifest(workspace)
    stage = begin_stage(workspace, "locked-evaluation", {"frozen_manifest": file_hash(workspace / "frozen-manifest.json")}, "g2-3-r1")
    started = time.perf_counter()
    sentences = generate_sentence_examples("locked")
    links = generate_link_examples("locked")
    calibration = _calibration(workspace)
    methods: dict[str, object] = {}
    prediction_output = {}
    for name, _recurrent in VARIANTS:
        model = _load(workspace, name)
        sentence_outputs = _prediction_shards(
            workspace,
            name,
            "sentences",
            lambda start, end, current=model: current.forward(tuple(item.source for item in sentences[start:end]), calibration.graph_confidence, calibration.graph_margin),
            len(sentences),
            16,
        )
        link_outputs = _prediction_shards(
            workspace,
            name,
            "links",
            lambda start, end, current=model: tuple(
                current.link(item.source, item.fragment_spans, item.public_candidates, calibration.link_confidence, calibration.link_margin)
                for item in links[start:end]
            ),
            len(links),
            16,
        )
        sentence = sentence_metrics(sentences, sentence_outputs)
        link = link_metrics(links, link_outputs)
        prediction_hash = digest({"sentence": _json_prediction(sentence_outputs), "links": [[asdict(link) for link in row] for row in link_outputs]})
        methods[name] = {"sentence": sentence, "link": link, "prediction_hash": prediction_hash}
        prediction_output[name] = {"sentence": _json_prediction(sentence_outputs), "links": [[asdict(link) for link in row] for row in link_outputs]}
    elapsed = time.perf_counter() - started
    memory = rss_mb()
    selected = manifest["operational"]
    passed, checks = gates(methods[selected]["sentence"], methods[selected]["link"], elapsed, memory)
    advantage = (
        methods["hierarchical"]["sentence"]["all_case_exact"] - methods["nonrecurrent"]["sentence"]["all_case_exact"] >= 0.05
        and methods["hierarchical"]["link"]["link_exact"] - methods["nonrecurrent"]["link"]["link_exact"] >= 0.03
    )
    classification = "G2.3-A" if passed else "G2.3-B-LOCAL-EXTRACTION"
    classification += " / G2.3-H-PASS" if advantage else " / G2.3-H-NOT-DEMONSTRATED"
    write_json(workspace / "locked-predictions.json", prediction_output)
    result = {
        "classification": classification,
        "operational": selected,
        "methods": methods,
        "gates": checks,
        "runtime_seconds": elapsed,
        "peak_rss_mb": memory,
        "network_calls": 0,
    }
    write_json(result_path, result)
    checkpoint_stage(workspace, stage, status="completed", artifacts={"locked_results": file_hash(result_path)})
    return result


def verify(workspace: Path) -> dict[str, object]:
    _verify_manifest(workspace)
    stored = json.loads((workspace / "locked-results.json").read_text(encoding="utf-8"))
    sentences = generate_sentence_examples("locked")
    links = generate_link_examples("locked")
    calibration = _calibration(workspace)
    for name, _recurrent in VARIANTS:
        model = _load(workspace, name)
        sentence_outputs = _predict(model, sentences, calibration.graph_confidence, calibration.graph_margin)
        link_outputs = tuple(
            model.link(item.source, item.fragment_spans, item.public_candidates, calibration.link_confidence, calibration.link_margin)
            for item in links
        )
        current = digest({"sentence": _json_prediction(sentence_outputs), "links": [[asdict(link) for link in row] for row in link_outputs]})
        if current != stored["methods"][name]["prediction_hash"]:
            raise RuntimeError(f"nondeterministic predictions: {name}")
    result = {"ok": True, "classification": stored["classification"]}
    write_json(workspace / "verification.json", result)
    return result
