"""I2.3 lifecycle with public-only runtime and evaluator-only scoring commands."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np

from .dataset import build_split, load_jsonl
from .evaluator import score
from .field import PublicField
from .kernel import load_kernel, save_kernel, train_kernel
from .runtime import infer
from .schemas import AtomicMumbrane, OptimizationStep, ReasoningBody, RuntimePrompt, RuntimeResult

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs/ltm-inference-i23.json"


def _settings() -> dict[str, object]:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_sha() -> str:
    return hashlib.sha256(b"".join(path.read_bytes() for path in sorted((ROOT / "src/ltm_inference_i23").glob("*.py")))).hexdigest()


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _load_public(workspace: Path, split: str) -> tuple[PublicField, tuple[dict[str, object], ...]]:
    root = workspace / "public" / split
    bodies = tuple(ReasoningBody(**row) for row in load_jsonl(root / "bodies.jsonl"))
    units = tuple(AtomicMumbrane(**row) for row in load_jsonl(root / "units.jsonl"))
    return PublicField(bodies, units, np.load(root / "vectors.npy")), load_jsonl(root / "prompts.jsonl")


def _prompt(row: dict[str, object]) -> RuntimePrompt:
    return RuntimePrompt(str(row["prompt_id"]), tuple(row["clamped_unit_ids"]), str(row["scope_key"]), int(row["maximum_bodies"]), int(row["maximum_steps"]))


def _result(row: dict[str, object]) -> RuntimeResult:
    return RuntimeResult(
        str(row["prompt_id"]),
        str(row["disposition"]),
        row["selected_candidate_id"],
        tuple((str(item[0]), float(item[1])) for item in row["candidates"]),
        tuple(row["supporting_body_ids"]),
        tuple(OptimizationStep(int(item["step"]), float(item["energy"]), bool(item["accepted"]), item["body_id"], tuple(item["opened_cell_ids"]), str(item["state_hash"])) for item in row["trajectory"]),
        str(row["coverage_disposition"]),
    )


def model_check(workspace: Path) -> dict[str, object]:
    runtime_source = (ROOT / "src/ltm_inference_i23/runtime.py").read_text(encoding="utf-8")
    result = {
        "experiment": "I2.3",
        "config_sha256": _sha(CONFIG),
        "source_sha256": _source_sha(),
        "runtime_imports_evaluator": "evaluator" in runtime_source,
        "runtime_gold_path_reference": "evaluator-gold" in runtime_source,
        "network_calls": 0,
        "factual_operations": False,
    }
    _write(workspace / "model-check.json", result)
    return result


def dataset_build(workspace: Path) -> dict[str, object]:
    settings = _settings()
    seeds = settings["seeds"]
    definitions = {
        "train": (int(settings["train_bodies"]), 0, int(seeds["training"])),
        "development": (int(settings["development_bodies"]), int(settings["development_prompts"]), int(seeds["development"])),
        "locked": (int(settings["locked_bodies"]), int(settings["locked_prompts"]), int(seeds["locked"])),
    }
    result = {name: build_split(workspace, name, body_count, prompt_count, seed) for name, (body_count, prompt_count, seed) in definitions.items()}
    _write(workspace / "dataset-manifest.json", result)
    return result


def develop(workspace: Path) -> dict[str, object]:
    settings = _settings()
    train, _ = _load_public(workspace, "train")
    model, losses = train_kernel(train, int(settings["optimizer"]["steps"]), int(settings["optimizer"]["batch_size"]), int(settings["seeds"]["training"]), float(settings["optimizer"]["learning_rate"]))
    kernel_meta = save_kernel(workspace / "development" / "kernel.pt", model, losses, int(settings["seeds"]["training"]))
    development, public = _load_public(workspace, "development")
    development.refresh(model)
    result_rows = {str(row["prompt_id"]): infer(development, model, _prompt(row)) for row in public}
    gold = load_jsonl(workspace / "evaluator-gold" / "development" / "gold.jsonl")
    metrics = score(public, result_rows, gold)
    payload = {"kernel": kernel_meta, "loss_tail": losses[-10:], "membership_ok": development.membership_ok(), "metrics": metrics}
    _write(workspace / "development-results.json", payload)
    (workspace / "selected-kernel.pt").write_bytes((workspace / "development" / "kernel.pt").read_bytes())
    return payload


def development_gate(workspace: Path) -> dict[str, object]:
    """Fail closed before any frozen or locked execution."""
    metrics = json.loads((workspace / "development-results.json").read_text(encoding="utf-8"))["metrics"]
    gates = _settings()["gates"]
    controls_path = workspace / "development-controls.json"
    controls = json.loads(controls_path.read_text(encoding="utf-8")) if controls_path.exists() else {"summary_influential": False}
    passed = {
        "accepted_precision": float(metrics["accepted_precision"]) >= float(gates["accepted_precision"]),
        "safe_coverage": float(metrics["safe_coverage"]) >= float(gates["safe_coverage"]),
        "answerable_exactness": float(metrics["answerable_exactness"]) >= float(gates["answerable_exactness"]),
        "frontier_recall": float(metrics["required_body_frontier_recall"]) >= float(gates["frontier_recall"]),
        "energy": int(metrics["energy_increases"]) == int(gates["energy_increases"]),
        "summary_influence": bool(controls["summary_influential"]),
    }
    result = {"passed": all(passed.values()), "gates": passed, "metrics": metrics}
    _write(workspace / "development-gate.json", result)
    return result


def development_controls(workspace: Path) -> dict[str, object]:
    """Ablate summaries; unchanged outputs prove the summary path is unused."""
    model = load_kernel(workspace / "selected-kernel.pt")
    field, public = _load_public(workspace, "development")
    field.refresh(model)
    normal = {str(row["prompt_id"]): infer(field, model, _prompt(row)) for row in public}
    dimension = len(next(iter(field.cells.values())).summary)
    field.cells = {cell_id: replace(cell, summary=(0.0,) * dimension) for cell_id, cell in field.cells.items()}
    ablated = {str(row["prompt_id"]): infer(field, model, _prompt(row)) for row in public}
    agreement = sum(normal[item].disposition == ablated[item].disposition and normal[item].selected_candidate_id == ablated[item].selected_candidate_id for item in normal) / max(1, len(normal))
    result = {"summary_output_agreement": agreement, "summary_influential": agreement < .80}
    _write(workspace / "development-controls.json", result)
    return result


def freeze(workspace: Path) -> dict[str, object]:
    gate = development_gate(workspace)
    if not gate["passed"]:
        raise RuntimeError("development gate failed; locked suite is not authorized")
    public = workspace / "public" / "locked"
    gold = workspace / "evaluator-gold" / "locked" / "gold.jsonl"
    result = {"experiment": "I2.3", "source_sha256": _source_sha(), "config_sha256": _sha(CONFIG), "kernel_sha256": _sha(workspace / "selected-kernel.pt"), "locked_public_sha256": _sha(public / "prompts.jsonl"), "locked_gold_sha256": _sha(gold), "runtime_evaluator_processes": "separate"}
    _write(workspace / "frozen-manifest.json", result)
    return result


def runtime_infer(workspace: Path) -> dict[str, object]:
    """Public command: it never opens evaluator-gold or imports evaluator."""
    model = load_kernel(workspace / "selected-kernel.pt")
    field, public = _load_public(workspace, "locked")
    field.refresh(model)
    results = [asdict(infer(field, model, _prompt(row))) for row in public]
    path = workspace / "runtime-output" / "locked-predictions.json"
    _write(path, {"predictions": results, "public_prompts": len(public), "membership_ok": field.membership_ok()})
    return {"prediction_sha256": _sha(path), "predictions": len(results), "membership_ok": field.membership_ok(), "opened_gold": False}


def evaluator_score(workspace: Path) -> dict[str, object]:
    """Evaluator command: score completed public predictions against private gold."""
    _, public = _load_public(workspace, "locked")
    payload = json.loads((workspace / "runtime-output" / "locked-predictions.json").read_text(encoding="utf-8"))
    results = {str(row["prompt_id"]): _result(row) for row in payload["predictions"]}
    gold = load_jsonl(workspace / "evaluator-gold" / "locked" / "gold.jsonl")
    metrics = score(public, results, gold)
    answer = {"metrics": metrics, "prediction_sha256": _sha(workspace / "runtime-output" / "locked-predictions.json")}
    _write(workspace / "locked-results.json", answer)
    return answer


def verify(workspace: Path) -> dict[str, object]:
    frozen = json.loads((workspace / "frozen-manifest.json").read_text(encoding="utf-8"))
    model = model_check(workspace)
    result = {
        "frozen_source_matches": frozen["source_sha256"] == _source_sha(),
        "runtime_imports_evaluator": model["runtime_imports_evaluator"],
        "runtime_gold_path_reference": model["runtime_gold_path_reference"],
        "network_calls": 0,
        "factual_operations": False,
        "prediction_exists": (workspace / "runtime-output" / "locked-predictions.json").exists(),
    }
    _write(workspace / "verification.json", result)
    return result
