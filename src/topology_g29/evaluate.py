"""G2.9 immutable lifecycle and evaluator-separated fail-fast kernel run."""

from __future__ import annotations

import hashlib
import json
import resource
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

import torch

from .atom_bank import ATOM_BANK_V1, ATOM_BANK_V11
from .dataset import build_split, load_gold, load_runtime, production_signature
from .encoder import AdaptedMiniLM, assert_model_hashes
from .metrics import evaluate, full_passes, kernel_passes
from .model import GoldenQueryKernel
from .report import write_report
from .runtime import compile_source, encode_query_bank
from .training import train_kernel


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _source_hash() -> str:
    digest = hashlib.sha256()
    for path in sorted(Path("src/topology_g29").glob("*.py")):
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _rss_mb() -> float:
    amount = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return amount / (1024 * 1024) if sys.platform == "darwin" else amount / 1024


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
        temporary = Path(handle.name)
        json.dump(value, handle, indent=2, sort_keys=True, default=str)
        handle.write("\n")
    temporary.replace(path)


def _artifact_row(artifact) -> dict[str, object]:
    return {"source_id": artifact.source_id, "disposition": artifact.disposition, "prediction": asdict(artifact.prediction) if artifact.prediction else None, "failure_codes": artifact.failure_codes, "operator_matches": [asdict(item) for item in artifact.operator_matches], "role_matches": [asdict(item) for item in artifact.role_matches], "field_program": artifact.accepted_field_program is not None, "operation_count": len(artifact.g1_operations)}


def model_check(workspace: Path) -> dict[str, object]:
    if (workspace / "model-check.json").exists():
        raise RuntimeError("model check already exists")
    torch.set_num_threads(4)
    hashes = assert_model_hashes()
    encoder = AdaptedMiniLM().eval()
    kernel = GoldenQueryKernel(ATOM_BANK_V1).eval()
    tokens = encoder.tokenize(["A fact supports a claim."])
    tokens.pop("offset_mapping")
    first = encoder(tokens["input_ids"], tokens["attention_mask"])
    second = encoder(tokens["input_ids"], tokens["attention_mask"])
    anchors = encode_query_bank(encoder, kernel)
    if not torch.equal(first, second) or anchors.shape[0] != 18 + len(kernel.layout.role_keys) or not encoder.frozen_parameters_unchanged():
        raise RuntimeError("G2.9 model preflight failed")
    result = {"hashes": hashes, "hidden_size": 384, "one_forward_per_sentence": True, "frozen_lower_layers": True, "trainable_upper_layers": True, "dynamic_queries": 54, "named_role_queries": len(kernel.layout.role_keys) * 3, "deterministic": True}
    _write(workspace / "model-check.json", result)
    return result


def atom_bank_build(workspace: Path) -> dict[str, object]:
    if (workspace / "atom-bank-v1.json").exists():
        raise RuntimeError("AtomBank already exists")
    _write(workspace / "atom-bank-v1.json", asdict(ATOM_BANK_V1))
    _write(workspace / "atom-bank-v1.1.json", asdict(ATOM_BANK_V11))
    return {"v1": ATOM_BANK_V1.bank_hash, "v1.1": ATOM_BANK_V11.bank_hash, "operators": len(ATOM_BANK_V1.operators), "roles": sum(len(item.roles) for item in ATOM_BANK_V1.operators)}


def dataset_build(workspace: Path) -> dict[str, object]:
    if (workspace / "dataset-manifest.json").exists():
        raise RuntimeError("development data already exists")
    summary = {split: build_split(workspace, split) for split in ("train", "development")}
    train = load_runtime(workspace / "train" / "inputs.jsonl")
    development = load_runtime(workspace / "development" / "inputs.jsonl")
    if {production_signature(item.text) for item in train} & {production_signature(item.text) for item in development}:
        raise RuntimeError("G2.9 train/development production overlap")
    result = {"splits": summary, "atom_bank_hash": ATOM_BANK_V1.bank_hash, "source_hash": _source_hash(), "challenge_fraction": .20}
    _write(workspace / "dataset-manifest.json", result)
    return result


def _load(workspace: Path, name: str = "kernel-checkpoint.pt"):
    encoder = AdaptedMiniLM()
    kernel = GoldenQueryKernel(ATOM_BANK_V1)
    state = torch.load(workspace / name, map_location="cpu", weights_only=False)
    encoder.load_state_dict(state["encoder"]); kernel.load_state_dict(state["kernel"])
    return kernel.eval(), encoder.eval()


def _infer(workspace: Path, kernel, encoder, sources, split: str):
    # The operator/role query bank is made once from the frozen checkpoint. It
    # is distinct from the exactly-one source pass invariant.
    with torch.no_grad():
        anchors = encode_query_bank(encoder, kernel)
    root = workspace / "vector-sidecars" / split
    return tuple(compile_source(kernel, encoder, anchors, source, ATOM_BANK_V1, root) for source in sources)


def kernel_develop(workspace: Path) -> dict[str, object]:
    output = workspace / "kernel-development-results.json"
    if output.exists():
        raise RuntimeError("kernel development already exists")
    if not (workspace / "dataset-manifest.json").exists():
        dataset_build(workspace)
    sources = load_runtime(workspace / "train" / "inputs.jsonl")
    gold = load_gold(workspace / "train" / "gold" / "gold.jsonl")
    kernel, encoder, summary = train_kernel(workspace, ATOM_BANK_V1, sources, gold)
    development = load_runtime(workspace / "development" / "inputs.jsonl")
    artifacts = _infer(workspace, kernel, encoder, development, "development")
    metrics = evaluate(load_gold(workspace / "development" / "gold" / "gold.jsonl"), artifacts)
    passed = kernel_passes(metrics)
    result = {"stage": "kernel-development", "cases": len(artifacts), "metrics": metrics, "classification": "G2.9-KERNEL-PASS" if passed else "G2.9-B — POST-ATTENTION GOLDEN-COMPARATOR FAILURE", "kernel_passed": passed, "training": asdict(summary), "peak_rss_mb": _rss_mb(), "model_hashes": assert_model_hashes()}
    _write(workspace / "kernel-development-predictions.json", [_artifact_row(item) for item in artifacts])
    _write(output, result)
    return result


def kernel_freeze(workspace: Path) -> dict[str, object]:
    development = json.loads((workspace / "kernel-development-results.json").read_text())
    if not development["kernel_passed"]:
        raise RuntimeError("kernel freeze refused after development failure")
    output = workspace / "kernel-frozen-manifest.json"
    if output.exists():
        raise RuntimeError("kernel is already frozen")
    result = {"source_hash": _source_hash(), "config_hash": _hash(Path("configs/topology-g2-9.json")), "checkpoint_hash": _hash(workspace / "kernel-checkpoint.pt"), "development_hash": _hash(workspace / "kernel-development-results.json"), "atom_bank_hash": ATOM_BANK_V1.bank_hash, "model_hashes": assert_model_hashes(), "torch": torch.__version__, "python": sys.version}
    _write(output, result)
    return result


def _verify_kernel_freeze(workspace: Path) -> None:
    manifest = json.loads((workspace / "kernel-frozen-manifest.json").read_text())
    required = {"source_hash": _source_hash(), "config_hash": _hash(Path("configs/topology-g2-9.json")), "checkpoint_hash": _hash(workspace / "kernel-checkpoint.pt"), "atom_bank_hash": ATOM_BANK_V1.bank_hash}
    if any(manifest[key] != value for key, value in required.items()):
        raise RuntimeError("frozen G2.9 kernel hash mismatch")
    assert_model_hashes()


def kernel_locked_suite_build(workspace: Path) -> dict[str, int]:
    _verify_kernel_freeze(workspace)
    return build_split(workspace, "kernel_locked")


def kernel_evaluate(workspace: Path) -> dict[str, object]:
    _verify_kernel_freeze(workspace)
    output = workspace / "kernel-results.json"
    if output.exists():
        raise RuntimeError("locked kernel evaluation already exists")
    kernel, encoder = _load(workspace)
    sources = load_runtime(workspace / "kernel_locked" / "inputs.jsonl")
    artifacts = _infer(workspace, kernel, encoder, sources, "kernel-locked")
    metrics = evaluate(load_gold(workspace / "kernel_locked" / "gold" / "gold.jsonl"), artifacts)
    passed = kernel_passes(metrics)
    result = {"stage": "kernel-locked", "cases": len(artifacts), "metrics": metrics, "classification": "G2.9-KERNEL-PASS" if passed else "G2.9-B — POST-ATTENTION GOLDEN-COMPARATOR FAILURE", "kernel_passed": passed, "peak_rss_mb": _rss_mb()}
    _write(workspace / "kernel-predictions.json", [_artifact_row(item) for item in artifacts])
    _write(output, result)
    return result


def develop(workspace: Path) -> dict[str, object]:
    kernel = json.loads((workspace / "kernel-results.json").read_text())
    if not kernel["kernel_passed"]:
        raise RuntimeError("full compilation is not authorized after a failed locked kernel")
    result = {"stage": "full-development", "classification": "G2.9-FULL-DEVELOPMENT-PENDING", "reason": "Stage B-D implementation follows only an empirical kernel pass"}
    _write(workspace / "development-results.json", result)
    return result


def freeze(workspace: Path) -> dict[str, object]:
    if not (workspace / "development-results.json").exists():
        raise RuntimeError("full development is required")
    output = workspace / "frozen-manifest.json"
    if output.exists():
        raise RuntimeError("full experiment already frozen")
    result = {"source_hash": _source_hash(), "config_hash": _hash(Path("configs/topology-g2-9.json")), "kernel_manifest_hash": _hash(workspace / "kernel-frozen-manifest.json"), "atom_bank_v1": ATOM_BANK_V1.bank_hash, "atom_bank_v1.1": ATOM_BANK_V11.bank_hash, "model_hashes": assert_model_hashes()}
    _write(output, result)
    return result


def locked_suite_build(workspace: Path) -> dict[str, int]:
    if not (workspace / "frozen-manifest.json").exists():
        raise RuntimeError("full freeze is required")
    return build_split(workspace, "locked")


def evaluate_locked(workspace: Path) -> dict[str, object]:
    if (workspace / "locked-results.json").exists():
        raise RuntimeError("second locked evaluation refused")
    kernel, encoder = _load(workspace)
    sources = load_runtime(workspace / "locked" / "inputs.jsonl")
    artifacts = _infer(workspace, kernel, encoder, sources, "locked")
    metrics = evaluate(load_gold(workspace / "locked" / "gold" / "gold.jsonl"), artifacts)
    passed = full_passes(metrics)
    result = {"stage": "full-locked", "cases": len(artifacts), "metrics": metrics, "classification": "G2.9-A — CONTROLLED G2 PASS" if passed else "G2.9-F — SAFE BUT LOW COVERAGE", "peak_rss_mb": _rss_mb()}
    _write(workspace / "locked-predictions.json", [_artifact_row(item) for item in artifacts]); _write(workspace / "locked-results.json", result)
    return result


def migrate(workspace: Path) -> dict[str, object]:
    if not (workspace / "locked-results.json").exists():
        raise RuntimeError("locked evaluation is required before migration")
    result = {"old_bank_hash": ATOM_BANK_V1.bank_hash, "new_bank_hash": ATOM_BANK_V11.bank_hash, "disposition": "not_authorized: document composition is not implemented in this kernel-only branch"}
    _write(workspace / "migration-results.json", result)
    return result


def integrate(workspace: Path) -> dict[str, object]:
    if not (workspace / "migration-results.json").exists():
        raise RuntimeError("migration stage is required")
    result = {"disposition": "not_authorized: no full compiler/migration pass exists"}
    _write(workspace / "integration-results.json", result)
    return result


def verify(workspace: Path) -> dict[str, object]:
    if not (workspace / "kernel-predictions.json").exists():
        raise RuntimeError("locked kernel predictions required")
    kernel, encoder = _load(workspace)
    sources = load_runtime(workspace / "kernel_locked" / "inputs.jsonl")
    replay = [_artifact_row(item) for item in _infer(workspace, kernel, encoder, sources, "verification")]
    expected = json.loads((workspace / "kernel-predictions.json").read_text())
    result = {"semantic_replay_equal": replay == expected, "atom_bank_hash": ATOM_BANK_V1.bank_hash}
    _write(workspace / "verification.json", result)
    if not result["semantic_replay_equal"]:
        raise RuntimeError("G2.9 replay differs")
    return result


def run_all(workspace: Path) -> dict[str, object]:
    workspace.mkdir(parents=True, exist_ok=True)
    if not (workspace / "model-check.json").exists(): model_check(workspace)
    if not (workspace / "dataset-manifest.json").exists(): dataset_build(workspace)
    if not (workspace / "atom-bank-v1.json").exists(): atom_bank_build(workspace)
    development = kernel_develop(workspace) if not (workspace / "kernel-development-results.json").exists() else json.loads((workspace / "kernel-development-results.json").read_text())
    if not development["kernel_passed"]:
        write_report(workspace, Path("docs/experiments/gaps/g02-9/report.md")); return development
    if not (workspace / "kernel-frozen-manifest.json").exists(): kernel_freeze(workspace)
    if not (workspace / "kernel_locked" / "inputs.jsonl").exists(): kernel_locked_suite_build(workspace)
    locked = kernel_evaluate(workspace) if not (workspace / "kernel-results.json").exists() else json.loads((workspace / "kernel-results.json").read_text())
    if not locked["kernel_passed"]:
        write_report(workspace, Path("docs/experiments/gaps/g02-9/report.md")); return locked
    # Full deployment stages refuse to claim authorization until their explicit
    # Stage B-D implementation is supplied and independently frozen.
    develop(workspace)
    write_report(workspace, Path("docs/experiments/gaps/g02-9/report.md"))
    return locked
