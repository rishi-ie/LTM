"""Fail-fast G2.11 basis lifecycle."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from .basis import build_basis, verify_basis
from .dataset import build_split
from .encoder import OnePassMiniLM, assert_model_hashes
from .measure import AtomicMeasurementHead


def _load_examples(path: Path):
    from .dataset import load

    return load(path)


def _checkpoint_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m topology_g211")
    parser.add_argument(
        "command",
        choices=(
            "basis-build", "basis-verify", "dataset-build", "model-check",
            "kernel-develop", "kernel-freeze", "kernel-locked-suite-build", "kernel-evaluate",
            "develop", "freeze", "locked-suite-build", "evaluate", "verify", "report", "run-all",
        ),
    )
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)
    manifest = build_basis()
    if args.command == "basis-build":
        destination = args.workspace / "atomic-basis.json"
        if destination.exists():
            raise RuntimeError("BASIS_ALREADY_EXISTS")
        _write(destination, asdict(manifest))
        return 0
    if args.command == "basis-verify":
        result = verify_basis(manifest)
        _write(args.workspace / "basis-verification.json", result)
        return 0
    if args.command == "dataset-build":
        result = {split: build_split(args.workspace, split) for split in ("train", "development", "kernel_locked", "locked")}
        _write(args.workspace / "dataset-manifest.json", result)
        return 0
    if args.command == "kernel-develop":
        from .training import save_summary, train_kernel

        input_path = args.workspace / "datasets" / "train" / "inputs.jsonl"
        if not input_path.exists():
            build_split(args.workspace, "train")
        summary = train_kernel(args.workspace, _load_examples(input_path), steps=1200)
        save_summary(args.workspace, summary)
        return 0
    if args.command == "kernel-freeze":
        checkpoint = args.workspace / "kernel-checkpoint.pt"
        if not checkpoint.exists():
            raise RuntimeError("KERNEL_CHECKPOINT_MISSING")
        frozen_manifest = {
            "basis_sha256": manifest.basis_sha256,
            "checkpoint_sha256": _checkpoint_digest(checkpoint),
            "model_hashes": assert_model_hashes(),
            "frozen": True,
        }
        destination = args.workspace / "kernel-frozen-manifest.json"
        if destination.exists():
            raise RuntimeError("KERNEL_ALREADY_FROZEN")
        _write(destination, frozen_manifest)
        return 0
    if args.command == "kernel-locked-suite-build":
        source = args.workspace / "datasets" / "kernel_locked" / "inputs.jsonl"
        if not source.exists():
            build_split(args.workspace, "kernel_locked")
        rows = _load_examples(source)
        public = tuple(
            {"source_id": row.source_id, "text": row.text, "source_hash": row.source_hash, "spans": [asdict(span) for span in row.spans]}
            for row in rows
        )
        _write(args.workspace / "kernel-locked" / "public-inputs.json", public)
        _write(args.workspace / "kernel-locked" / "evaluator-gold.json", [asdict(row) for row in rows])
        return 0
    if args.command == "kernel-evaluate":
        from .inference import load_checkpoint, predict_example
        from .metrics import score_examples

        checkpoint = args.workspace / "kernel-checkpoint.pt"
        if not checkpoint.exists():
            raise RuntimeError("KERNEL_CHECKPOINT_MISSING")
        path = args.workspace / "datasets" / "kernel_locked" / "inputs.jsonl"
        if not path.exists():
            raise RuntimeError("KERNEL_LOCKED_SUITE_MISSING")
        rows = _load_examples(path)
        encoder, head = load_checkpoint(checkpoint)
        patches = tuple(predict_example(encoder, head, row) for row in rows)
        result = score_examples(rows, patches)
        _write(args.workspace / "kernel-results.json", result)
        _write(args.workspace / "kernel-predictions.json", [asdict(item) for item in patches])
        return 0
    if args.command in {"develop", "freeze", "locked-suite-build", "evaluate", "verify", "report", "run-all"}:
        if args.command == "develop":
            return main(["kernel-develop", "--workspace", str(args.workspace)])
        if args.command == "freeze":
            return main(["kernel-freeze", "--workspace", str(args.workspace)])
        if args.command == "locked-suite-build":
            return main(["kernel-locked-suite-build", "--workspace", str(args.workspace)])
        if args.command == "evaluate":
            return main(["kernel-evaluate", "--workspace", str(args.workspace), "--offline"])
        if args.command == "verify":
            checks = verify_basis(manifest)
            checkpoint = args.workspace / "kernel-checkpoint.pt"
            checks["checkpoint_present"] = checkpoint.exists()
            checks["model_hashes"] = assert_model_hashes()
            _write(args.workspace / "verification.json", checks)
            return 0
        if args.command == "report":
            results = {}
            for name in ("kernel-results.json", "model-check.json", "dataset-manifest.json"):
                path = args.workspace / name
                if path.exists():
                    results[name.removesuffix(".json")] = json.loads(path.read_text(encoding="utf-8"))
            _write(args.workspace / "report.json", results)
            return 0
        if args.command == "run-all":
            for stage in ("basis-build", "basis-verify", "dataset-build", "model-check", "kernel-develop", "kernel-freeze", "kernel-locked-suite-build", "kernel-evaluate", "verify", "report"):
                try:
                    main([stage, "--workspace", str(args.workspace), "--offline"])
                except RuntimeError as error:
                    if "already" not in str(error).lower():
                        raise
                if stage == "kernel-evaluate":
                    result_path = args.workspace / "kernel-results.json"
                    result = json.loads(result_path.read_text(encoding="utf-8"))
                    if result["accepted_precision"] < 0.98 or result["safe_coverage"] < 0.95 or result["severe_errors"]:
                        _write(args.workspace / "classification.json", {
                            "classification": "G2.11-B",
                            "reason": "atomic kernel gate failed",
                            "kernel_results": result,
                        })
                        return 0
            return 0
    import torch

    torch.set_num_threads(4)
    hashes = assert_model_hashes()
    first = OnePassMiniLM().eval()
    second = OnePassMiniLM().eval()
    state_a = first.encode("model-check", "claim_A precedes claim_B.")
    state_b = second.encode("model-check", "claim_A precedes claim_B.")
    head = AtomicMeasurementHead(len(manifest.features))
    trainable = sum(parameter.numel() for parameter in head.parameters() if parameter.requires_grad)
    result = {
        "hashes": hashes,
        "hidden_size": len(state_a.sentence_state),
        "one_pass_first": state_a.forward_count == 1,
        "one_pass_second": state_b.forward_count == 1,
        "deterministic_output": state_a.token_states == state_b.token_states,
        "lower_layers_frozen": all(
            not parameter.requires_grad
            for layer in list(first.model.encoder.layer)[:-2]
            for parameter in layer.parameters()
        ),
        "atomic_feature_count": len(manifest.features),
        "measurement_head_parameters": trainable,
        "measurement_head_limit": trainable <= 2_000_000,
    }
    _write(args.workspace / "model-check.json", result)
    if not all((result["one_pass_first"], result["one_pass_second"], result["deterministic_output"], result["lower_layers_frozen"], result["measurement_head_limit"])):
        raise RuntimeError("G2.11 model preflight failed")
    return 0
