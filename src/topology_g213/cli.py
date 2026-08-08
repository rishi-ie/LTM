from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import torch

from .dataset import build_split, load_evaluation, load_public, load_training
from .encoder import EXPECTED_HASHES, OnePassMiniLM, assert_model_hashes
from .inference import load_checkpoint, predict_case
from .metrics import classify, score_kernel
from .model import ConversationCompiler
from .registry import ACTIONS, ACTS
from .training import save_summary, train_kernel

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "topology-g2-13.json"


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _settings() -> dict[str, object]:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def model_check(workspace: Path) -> None:
    torch.set_num_threads(4)
    hashes = assert_model_hashes()
    first, second = OnePassMiniLM().eval(), OnePassMiniLM().eval()
    first_state, second_state = first.encode("g213-check", "I prefer concise answers."), second.encode("g213-check", "I prefer concise answers.")
    compiler = ConversationCompiler(first)
    result = {
        "hashes": hashes,
        "expected_hashes": EXPECTED_HASHES,
        "one_pass_first": first_state.forward_count == 1,
        "one_pass_second": second_state.forward_count == 1,
        "deterministic_output": first_state.token_states == second_state.token_states,
        "lower_layers_frozen": all(not parameter.requires_grad for layer in list(first.model.encoder.layer)[:-2] for parameter in layer.parameters()),
        "relation_heads": {"acts": len(ACTS), "actions": len(ACTIONS)},
        "trainable_parameters": sum(parameter.numel() for parameter in compiler.parameters() if parameter.requires_grad),
    }
    _write(workspace / "model-check.json", result)
    if not all((result["one_pass_first"], result["one_pass_second"], result["deterministic_output"], result["lower_layers_frozen"])):
        raise RuntimeError("G2.13_MODEL_CHECK_FAILED")


def dataset_build(workspace: Path) -> None:
    manifest = {split: build_split(workspace, split) for split in ("train", "development", "kernel_locked", "locked")}
    _write(workspace / "dataset-manifest.json", manifest)


def kernel_develop(workspace: Path) -> None:
    examples = load_training(workspace / "datasets" / "train" / "training.jsonl")
    settings = _settings()["training"]
    summary = train_kernel(workspace, examples, steps=int(settings["kernel_steps"]), warmup=int(settings["warmup_steps"]))
    save_summary(workspace, summary)


def kernel_freeze(workspace: Path) -> None:
    destination = workspace / "kernel-frozen-manifest.json"
    if destination.exists():
        raise RuntimeError("KERNEL_ALREADY_FROZEN")
    checkpoint = workspace / "kernel-checkpoint.pt"
    if not checkpoint.exists():
        raise RuntimeError("KERNEL_CHECKPOINT_MISSING")
    _write(destination, {"checkpoint_sha256": _hash(checkpoint), "config_sha256": _hash(CONFIG), "model_hashes": assert_model_hashes()})


def kernel_locked_suite_build(workspace: Path) -> None:
    root = workspace / "datasets" / "kernel_locked"
    if not (root / "public.jsonl").exists():
        build_split(workspace, "kernel_locked")
    _write(workspace / "kernel-locked-manifest.json", {"public_sha256": _hash(root / "public.jsonl"), "gold_sha256": _hash(root / "gold.jsonl"), "evaluator_only": True})


def kernel_evaluate(workspace: Path) -> dict[str, object]:
    cases = load_evaluation(workspace / "datasets" / "kernel_locked")
    public = load_public(workspace / "datasets" / "kernel_locked" / "public.jsonl")
    model = load_checkpoint(workspace / "kernel-checkpoint.pt")
    predictions = tuple(predict_case(model, case) for case in public)
    result = score_kernel(cases, predictions, _settings()["gates"])
    _write(workspace / "kernel-predictions.json", [asdict(prediction) for prediction in predictions])
    _write(workspace / "kernel-results.json", result)
    return result


def write_report(workspace: Path, classification: str | None = None) -> None:
    result = {}
    for name in ("model-check.json", "dataset-manifest.json", "kernel-training-summary.json", "kernel-results.json", "full-results.json", "lifecycle-results.json", "classification.json"):
        path = workspace / name
        if path.exists():
            result[name.removesuffix(".json")] = json.loads(path.read_text(encoding="utf-8"))
    if classification:
        result["classification"] = classification
    _write(workspace / "report.json", result)
    lines = ["# G2.13 — Conversational Mumbrane Compiler", "", f"**Classification:** **{result.get('classification', classification or 'PENDING')}**", ""]
    kernel = result.get("kernel-results", {})
    if kernel:
        lines.extend(["## Kernel result", "", "| Metric | Result |", "| --- | ---: |", f"| Accepted precision | `{kernel.get('accepted_precision', 0):.4f}` |", f"| Safe coverage | `{kernel.get('safe_coverage', 0):.4f}` |", f"| Discourse-act macro-F1 | `{kernel.get('act_macro_f1', 0):.4f}` |", f"| Memory-action macro-F1 | `{kernel.get('action_macro_f1', 0):.4f}` |", f"| Context accuracy | `{kernel.get('context_accuracy', 0):.4f}` |", f"| Disposition accuracy | `{kernel.get('disposition_accuracy', 0):.4f}` |", f"| Unsafe mutations | `{kernel.get('unsafe_mutations', 0)}` |"])
        if not kernel.get("kernel_passed", False):
            lines.extend(["", "The gold-span conversational kernel failed its mandatory gates. Per the fail-fast contract, raw span extraction, identity linking, lifecycle evaluation, and downstream handoff were not authorized."])
    (workspace / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m topology_g213")
    parser.add_argument("command", choices=("model-check", "dataset-build", "kernel-develop", "kernel-freeze", "kernel-locked-suite-build", "kernel-evaluate", "develop", "freeze", "locked-suite-build", "evaluate", "lifecycle-evaluate", "verify", "report", "resume", "run-all"))
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)
    workspace = args.workspace
    if args.command == "model-check":
        model_check(workspace)
    elif args.command == "dataset-build":
        dataset_build(workspace)
    elif args.command in {"kernel-develop", "develop"}:
        kernel_develop(workspace)
    elif args.command in {"kernel-freeze", "freeze"}:
        kernel_freeze(workspace)
    elif args.command in {"kernel-locked-suite-build", "locked-suite-build"}:
        kernel_locked_suite_build(workspace)
    elif args.command in {"kernel-evaluate", "evaluate"}:
        kernel_evaluate(workspace)
    elif args.command == "lifecycle-evaluate":
        _write(workspace / "lifecycle-results.json", {"authorized": False, "reason": "kernel boundary must pass first"})
    elif args.command == "verify":
        result = {"model_check": (workspace / "model-check.json").exists(), "dataset_manifest": (workspace / "dataset-manifest.json").exists(), "kernel_results": (workspace / "kernel-results.json").exists(), "frozen_manifest": (workspace / "kernel-frozen-manifest.json").exists(), "model_hashes": assert_model_hashes()}
        _write(workspace / "verification.json", result)
    elif args.command == "report":
        write_report(workspace)
    elif args.command in {"resume", "run-all"}:
        for stage, function in (("model-check", model_check), ("dataset-build", dataset_build), ("kernel-develop", kernel_develop), ("kernel-freeze", kernel_freeze), ("kernel-locked-suite-build", kernel_locked_suite_build)):
            try:
                function(workspace)
            except RuntimeError as error:
                if "already" not in str(error).lower():
                    raise
        result = kernel_evaluate(workspace)
        classification = classify(result)
        _write(workspace / "classification.json", {"classification": classification, "kernel_results": result})
        write_report(workspace, classification)
        if not result["kernel_passed"]:
            _write(workspace / "lifecycle-results.json", {"authorized": False, "reason": "kernel boundary failed"})
            return 0
        _write(workspace / "full-results.json", {"authorized": False, "classification": "G2.13-C — CONTENT OR SLOT EXTRACTION FAILURE", "reason": "raw extraction stage is not entered until the kernel passes; this run must be resumed after a new frozen kernel"})
    return 0
