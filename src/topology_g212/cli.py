"""Fail-fast G2.12 lifecycle."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import torch

from topology_g211.encoder import EXPECTED_HASHES, OnePassMiniLM, assert_model_hashes

from .dataset import build_split, load_evaluation, load_public, load_training
from .inference import load_checkpoint, predict_case
from .metrics import score_kernel
from .model import FactorizedCompiler
from .registry import RELATIONS, ROLES
from .training import save_summary, train_kernel

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "topology-g2-12.json"


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


def _model_check(workspace: Path) -> int:
    torch.set_num_threads(4)
    hashes = assert_model_hashes()
    first = OnePassMiniLM().eval()
    second = OnePassMiniLM().eval()
    text = "claim_alpha precedes claim_beta."
    first_state = first.encode("g212-model-check", text)
    second_state = second.encode("g212-model-check", text)
    model = FactorizedCompiler(first)
    trainable = sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
    result = {
        "hashes": hashes,
        "expected_hashes": EXPECTED_HASHES,
        "one_pass_first": first_state.forward_count == 1,
        "one_pass_second": second_state.forward_count == 1,
        "deterministic_output": first_state.token_states == second_state.token_states,
        "lower_layers_frozen": all(not parameter.requires_grad for layer in list(first.model.encoder.layer)[:-2] for parameter in layer.parameters()),
        "relation_count": len(RELATIONS),
        "role_count": len(ROLES),
        "trainable_parameters": trainable,
    }
    _write(workspace / "model-check.json", result)
    if not all((result["one_pass_first"], result["one_pass_second"], result["deterministic_output"], result["lower_layers_frozen"])):
        raise RuntimeError("G2.12 model preflight failed")
    return 0


def _kernel_evaluate(workspace: Path) -> dict[str, object]:
    settings = _settings()
    gates = settings["gates"]
    evaluator_cases = load_evaluation(workspace / "datasets" / "kernel_locked")
    public_cases = load_public(workspace / "datasets" / "kernel_locked" / "public.jsonl")
    model = load_checkpoint(workspace / "kernel-checkpoint.pt")
    predictions = tuple(predict_case(model, case) for case in public_cases)
    result = score_kernel(evaluator_cases, predictions, gates)
    _write(workspace / "kernel-predictions.json", [asdict(prediction) for prediction in predictions])
    _write(workspace / "kernel-results.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m topology_g212")
    parser.add_argument("command", choices=("model-check", "dataset-build", "kernel-develop", "kernel-freeze", "kernel-locked-suite-build", "kernel-evaluate", "develop", "freeze", "locked-suite-build", "evaluate", "verify", "report", "resume", "run-all"))
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)
    command = args.command
    workspace = args.workspace
    if command == "model-check":
        return _model_check(workspace)
    if command == "dataset-build":
        manifest = {split: build_split(workspace, split) for split in ("train", "development", "kernel_locked", "locked")}
        _write(workspace / "dataset-manifest.json", manifest)
        return 0
    if command == "kernel-develop":
        examples = load_training(workspace / "datasets" / "train" / "training.jsonl")
        summary = train_kernel(workspace, examples, steps=int(_settings()["training"]["kernel_steps"]), warmup=int(_settings()["training"]["warmup_steps"]))
        save_summary(workspace, summary)
        return 0
    if command == "kernel-freeze":
        checkpoint = workspace / "kernel-checkpoint.pt"
        if not checkpoint.exists():
            raise RuntimeError("KERNEL_CHECKPOINT_MISSING")
        destination = workspace / "kernel-frozen-manifest.json"
        if destination.exists():
            raise RuntimeError("KERNEL_ALREADY_FROZEN")
        _write(destination, {"checkpoint_sha256": _hash(checkpoint), "model_hashes": assert_model_hashes(), "config_sha256": _hash(CONFIG)})
        return 0
    if command == "kernel-locked-suite-build":
        source = workspace / "datasets" / "kernel_locked"
        if not (source / "public.jsonl").exists():
            build_split(workspace, "kernel_locked")
        _write(workspace / "kernel-locked-manifest.json", {"public": _hash(source / "public.jsonl"), "gold": _hash(source / "gold.jsonl"), "evaluator_only": True})
        return 0
    if command == "kernel-evaluate":
        _kernel_evaluate(workspace)
        return 0
    if command in {"develop", "freeze", "locked-suite-build", "evaluate"}:
        mapped = {"develop": "kernel-develop", "freeze": "kernel-freeze", "locked-suite-build": "kernel-locked-suite-build", "evaluate": "kernel-evaluate"}[command]
        return main([mapped, "--workspace", str(workspace), "--offline"])
    if command == "verify":
        result = {"model_check": (workspace / "model-check.json").exists(), "dataset_manifest": (workspace / "dataset-manifest.json").exists(), "kernel_results": (workspace / "kernel-results.json").exists(), "frozen_manifest": (workspace / "kernel-frozen-manifest.json").exists(), "model_hashes": assert_model_hashes()}
        _write(workspace / "verification.json", result)
        return 0
    if command == "report":
        result = {}
        for name in ("model-check.json", "dataset-manifest.json", "kernel-results.json", "kernel-training-summary.json"):
            path = workspace / name
            if path.exists():
                result[name.removesuffix(".json")] = json.loads(path.read_text(encoding="utf-8"))
        _write(workspace / "report.json", result)
        return 0
    if command == "resume":
        return main(["run-all", "--workspace", str(workspace), "--offline"])
    if command == "run-all":
        for stage in ("model-check", "dataset-build", "kernel-develop", "kernel-freeze", "kernel-locked-suite-build", "kernel-evaluate"):
            try:
                main([stage, "--workspace", str(workspace), "--offline"])
            except RuntimeError as error:
                if "already" not in str(error).lower():
                    raise
            if stage == "kernel-evaluate":
                result = json.loads((workspace / "kernel-results.json").read_text(encoding="utf-8"))
                if not result["kernel_passed"]:
                    _write(workspace / "classification.json", {"classification": "G2.12-B — FACTORIZED KERNEL FAILURE", "kernel_results": result})
                    main(["report", "--workspace", str(workspace)])
                    return 0
        for stage in ("verify", "report"):
            main([stage, "--workspace", str(workspace), "--offline"])
        return 0
    return 0
