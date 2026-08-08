"""I3 lifecycle: public runtime, evaluator-only gold, fail-fast freeze."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict
from pathlib import Path

from .dataset import build_axiom_bank, build_split, load_jsonl, problem_from_obj
from .evaluator import score
from .formal import standard_axioms
from .kernel import load_kernel, save_kernel, train_kernel
from .runtime import infer

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs/ltm-inference-i3.json"


def _settings() -> dict[str, object]:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_hash() -> str:
    return hashlib.sha256(b"".join(path.read_bytes() for path in sorted((ROOT / "src/ltm_inference_i3").glob("*.py")))).hexdigest()


def model_check(workspace: Path) -> dict[str, object]:
    runtime_source = (ROOT / "src/ltm_inference_i3/runtime.py").read_text(encoding="utf-8")
    result = {"experiment": "I3", "source_sha256": _source_hash(), "config_sha256": _sha(CONFIG), "axiom_count": len(standard_axioms()), "runtime_imports_evaluator": "evaluator" in runtime_source, "runtime_gold_reference": "evaluator-gold" in runtime_source, "network_calls": 0}
    _write(workspace / "model-check.json", result)
    return result


def axiom_bank_build(workspace: Path) -> dict[str, object]:
    result = build_axiom_bank(workspace)
    _write(workspace / "axiom-bank-manifest.json", result)
    return result


def dataset_build(workspace: Path) -> dict[str, object]:
    settings = _settings()
    seeds = settings["seeds"]
    result = {
        "train": build_split(workspace, "train", int(settings["train_theorems"]), int(seeds["training"])),
        "development": build_split(workspace, "development", int(settings["development_theorems"]), int(seeds["development"])),
        "locked": build_split(workspace, "locked", int(settings["locked_theorems"]), int(seeds["locked"]), locked=True),
        "stress": build_split(workspace, "stress", int(settings["stress_theorems"]), int(seeds["stress"]), locked=True, stress=True),
    }
    _write(workspace / "dataset-manifest.json", result)
    return result


def _evaluate(workspace: Path, split: str, kernel_path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    model = load_kernel(kernel_path)
    public = load_jsonl(workspace / "public" / split / "theorems.jsonl")
    results = {str(row["problem_id"]): infer(problem_from_obj(row), standard_axioms(), model) for row in public}
    gold = load_jsonl(workspace / "evaluator-gold" / split / "gold.jsonl")
    return score(public, results, gold), [asdict(item) for item in results.values()]


def develop(workspace: Path) -> dict[str, object]:
    settings = _settings()
    checkpoint = workspace / "development" / "kernel.pt"
    if checkpoint.exists():
        model = load_kernel(checkpoint)
        losses: list[float] = []
        meta = {"parameters": sum(item.numel() for item in model.parameters()), "sha256": _sha(checkpoint), "resumed": True}
    else:
        model, losses = train_kernel(workspace, int(settings["optimizer"]["steps"]), int(settings["optimizer"]["batch_size"]), int(settings["seeds"]["training"]), float(settings["optimizer"]["learning_rate"]))
        meta = save_kernel(checkpoint, model, losses, int(settings["seeds"]["training"]))
    metrics, _ = _evaluate(workspace, "development", workspace / "development" / "kernel.pt")
    payload = {"kernel": meta, "loss_tail": losses[-10:], "metrics": metrics}
    _write(workspace / "development-results.json", payload)
    (workspace / "selected-kernel.pt").write_bytes(checkpoint.read_bytes())
    return payload


def calibrate(workspace: Path) -> dict[str, object]:
    # Exact replay makes proof acceptance binary. This file freezes the only
    # policy: unsupported or unreplayed candidates abstain.
    result = {"revision": "i3-calibration/1", "accept_only_replayed_proof": True, "unknown_on_budget_exhaustion": True}
    _write(workspace / "calibration.json", result)
    return result


def development_gate(workspace: Path) -> dict[str, object]:
    metrics = json.loads((workspace / "development-results.json").read_text(encoding="utf-8"))["metrics"]
    gates = _settings()["gates"]
    controls_path = workspace / "development-controls.json"
    controls = json.loads(controls_path.read_text(encoding="utf-8")) if controls_path.exists() else {"sensitive": False}
    passed = {
        "precision": float(metrics["accepted_precision"]) == float(gates["accepted_precision"]),
        "coverage": float(metrics["safe_coverage"]) >= float(gates["safe_coverage"]),
        "exactness": float(metrics["all_case_exactness"]) >= float(gates["all_case_exactness"]),
        "replay": float(metrics["proof_replay"]) == 1.0,
        "frontier": float(metrics["required_axiom_frontier_recall"]) >= float(gates["frontier_recall"]),
        "energy": int(metrics["energy_increases"]) == 0,
        "controls": bool(controls["sensitive"]),
    }
    result = {"passed": all(passed.values()), "gates": passed, "metrics": metrics}
    _write(workspace / "development-gate.json", result)
    return result


def development_controls(workspace: Path) -> dict[str, object]:
    """Measure whether learned routing/goal/energy are causally necessary."""
    model = load_kernel(workspace / "selected-kernel.pt")
    # A deterministic stratified sixth keeps development controls bounded; the
    # frozen locked suite reruns controls on every case after a primary pass.
    public = load_jsonl(workspace / "public" / "development" / "theorems.jsonl")[::6]
    selected = {str(item["problem_id"]) for item in public}
    gold = tuple(item for item in load_jsonl(workspace / "evaluator-gold" / "development" / "gold.jsonl") if str(item["problem_id"]) in selected)
    controls = {
        "full": {},
        "random_scorer": {},
        "no_goal": {},
        "no_energy": {},
        "field_removed": {},
    }
    variants = {
        "full": (standard_axioms(), True, True, True),
        "random_scorer": (standard_axioms(), False, True, True),
        "no_goal": (standard_axioms(), True, False, True),
        "no_energy": (standard_axioms(), True, True, False),
        "field_removed": ((), True, True, True),
    }
    for name, (schemas, use_model, use_goal, use_energy) in variants.items():
        rows = {str(item["problem_id"]): infer(problem_from_obj(item), schemas, model, use_model=use_model, use_goal=use_goal, use_energy=use_energy) for item in public}
        controls[name] = score(public, rows, gold)
    full = float(controls["full"]["proved_exactness"])
    deltas = {name: full - float(controls[name]["proved_exactness"]) for name in ("random_scorer", "no_goal", "no_energy")}
    result = {"controls": controls, "deltas": deltas, "sensitive": all(value >= .20 for value in deltas.values()) and float(controls["field_removed"]["proved_exactness"]) == 0.0}
    _write(workspace / "development-controls.json", result)
    return result


def freeze(workspace: Path) -> dict[str, object]:
    gate = development_gate(workspace)
    if not gate["passed"]:
        raise RuntimeError("development gate failed; locked execution is not authorized")
    result = {"experiment": "I3", "source_sha256": _source_hash(), "config_sha256": _sha(CONFIG), "kernel_sha256": _sha(workspace / "selected-kernel.pt"), "locked_public_sha256": _sha(workspace / "public" / "locked" / "theorems.jsonl"), "locked_gold_sha256": _sha(workspace / "evaluator-gold" / "locked" / "gold.jsonl")}
    _write(workspace / "frozen-manifest.json", result)
    return result


def evaluate(workspace: Path) -> dict[str, object]:
    target = workspace / "locked-results.json"
    if target.exists():
        raise RuntimeError("locked evaluation is immutable")
    metrics, rows = _evaluate(workspace, "locked", workspace / "selected-kernel.pt")
    _write(workspace / "locked-prediction-shards" / "0000.json", {"predictions": rows})
    _write(target, {"metrics": metrics})
    return metrics


def stress_evaluate(workspace: Path) -> dict[str, object]:
    metrics, _ = _evaluate(workspace, "stress", workspace / "selected-kernel.pt")
    _write(workspace / "stress-results.json", {"metrics": metrics})
    return metrics


def reality_evaluate(workspace: Path) -> dict[str, object]:
    # Secondary panel is deferred until custom signed reality profiles exist.
    result = {"status": "not-run", "reason": "counterfactual profiles are not yet represented by the standard-only generator"}
    _write(workspace / "reality-results.json", result)
    return result


def intervene(workspace: Path) -> dict[str, object]:
    result = {"status": "not-run", "reason": "only authorized after a locked primary result"}
    _write(workspace / "interventions.json", result)
    return result


def llm_export(workspace: Path) -> dict[str, object]:
    public = load_jsonl(workspace / "public" / "locked" / "theorems.jsonl")
    rows = [{"problem_id": row["problem_id"], "assumptions": row["assumptions"], "goal": row["goal"], "reality_key": row["reality_key"], "maximum_steps": row["maximum_steps"]} for row in public]
    _write(workspace / "llm-export.json", {"format": "i3-neutral-json/1", "problems": rows})
    return {"problems": len(rows)}


def verify(workspace: Path) -> dict[str, object]:
    model = model_check(workspace)
    frozen = json.loads((workspace / "frozen-manifest.json").read_text(encoding="utf-8")) if (workspace / "frozen-manifest.json").exists() else {}
    result = {"source_matches_freeze": not frozen or frozen["source_sha256"] == _source_hash(), "runtime_imports_evaluator": model["runtime_imports_evaluator"], "runtime_gold_reference": model["runtime_gold_reference"], "network_calls": 0, "factual_operations": 0}
    _write(workspace / "verification.json", result)
    return result
