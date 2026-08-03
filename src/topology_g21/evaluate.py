from __future__ import annotations

import hashlib
import json
import resource
import sys
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np
import torch

from .dataset import (
    DIRECTIONS,
    DISPOSITIONS,
    LABELS,
    ROLE_LABELS,
    SCOPES,
    generate_cases,
    write_cases,
)
from .encode import encode_split, model_check, model_hashes
from .features import build_features
from .metrics import score
from .schemas import ReasoningCase, ReasoningPrediction
from .train import predict, train_model

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "topology-g2-1.json"


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temp.replace(path)


def _sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(split: str, workspace: Path, include_statement: bool = True) -> tuple[tuple[ReasoningCase, ...], np.ndarray]:
    cases = generate_cases(split)
    path = workspace / split / "embeddings.npz"
    if not path.exists(): encode_split(split, workspace)
    data = np.load(path)
    return cases, build_features(data["statement"], data["arguments"], data["mask"], include_statement)


def _predictions(method: str, model, x: np.ndarray, cases: tuple[ReasoningCase, ...]) -> tuple[ReasoningPrediction, ...]:
    output = predict(model, x)
    result = []
    for i, case in enumerate(cases):
        relation = LABELS[int(output["relation"][i].argmax())]
        direction = DIRECTIONS[int(output["direction"][i].argmax())]
        roles = tuple(ROLE_LABELS[int(output["roles"][i, slot].argmax())] for slot in range(len(case.arguments)))
        scope = SCOPES[int(output["scope"][i].argmax())]
        disposition = DISPOSITIONS[int(output["disposition"][i].argmax())]
        logits = output["relation"][i]; confidence = float(np.exp(logits.max() - np.logaddexp.reduce(logits)))
        emb = tuple(float(v) for v in output["embedding"][i]) if method == "projection" else None
        result.append(ReasoningPrediction(case.case_id, relation, direction, roles, scope, disposition, confidence, emb))
    return tuple(result)


def develop(workspace: Path) -> dict:
    train_cases, train_x = _load("train", workspace)
    dev_cases, dev_x = _load("development", workspace)
    candidates = []
    for nonlinear, name, grid in ((False, "linear", ((.001, 0), (.003, .0001))), (True, "projection", ((.001, .0001), (.003, .0001)))):
        for lr, wd in grid:
            model, info = train_model(train_x, train_cases, dev_x, dev_cases, nonlinear, lr, wd)
            rows = _predictions(name, model, dev_x, dev_cases)
            metrics = score(dev_cases, rows)
            candidates.append((name, model, info, metrics))
    candidates.sort(key=lambda row: (-row[3]["topology_agreement"], -row[3]["relation_macro_f1"], -row[3]["direction_accuracy"], row[2]["validation_loss"], row[2]["epochs"]))
    selected: dict[str, dict] = {}
    for name in ("linear", "projection"):
        item = next(row for row in candidates if row[0] == name)
        path = workspace / f"selected-{name}.pt"; path.parent.mkdir(parents=True, exist_ok=True)
        torch.save({"state": item[1].state_dict(), "input_dimension": train_x.shape[1], "role_count": len(ROLE_LABELS), "info": item[2]}, path)
        selected[name] = {"metrics": item[3], "info": item[2], "checkpoint_sha256": _sha(path)}
    operational = min(selected, key=lambda name: (-selected[name]["metrics"]["topology_agreement"], -selected[name]["metrics"]["relation_macro_f1"]))
    result = {"selected": selected, "operational": operational, "model": model_check()}
    _write(workspace / "development-results.json", result)
    return result


def freeze(workspace: Path) -> dict:
    result_path = workspace / "development-results.json"
    if not result_path.exists(): raise RuntimeError("run develop first")
    if (workspace / "frozen-manifest.json").exists(): raise RuntimeError("already frozen")
    sources = {str(p.relative_to(ROOT)): _sha(p) for p in sorted((ROOT / "src" / "topology_g21").glob("*.py"))}
    manifest = {"source_hashes": sources, "config_hash": _sha(CONFIG), "model_hashes": model_hashes(), "development_hash": _sha(result_path), "selected": json.loads(result_path.read_text())["selected"], "operational": json.loads(result_path.read_text())["operational"], "locked_ids": [c.case_id for c in generate_cases("locked")]}
    _write(workspace / "frozen-manifest.json", manifest)
    return manifest


def locked_suite_build(workspace: Path) -> dict:
    if not (workspace / "frozen-manifest.json").exists(): raise RuntimeError("freeze first")
    cases = generate_cases("locked")
    write_cases(cases, workspace / "locked" / "inputs.jsonl", False)
    write_cases(cases, workspace / "locked-gold" / "gold.jsonl", True)
    return {"cases": len(cases)}


def _load_checkpoint(workspace: Path, name: str, input_dimension: int):
    from .models import MultiHead
    state = torch.load(workspace / f"selected-{name}.pt", weights_only=True)
    model = MultiHead(input_dimension, len(ROLE_LABELS), name == "projection")
    model.load_state_dict(state["state"])
    return model


def evaluate_locked(workspace: Path) -> dict:
    path = workspace / "locked-results.json"
    if path.exists(): raise RuntimeError("locked evaluation already exists")
    manifest = json.loads((workspace / "frozen-manifest.json").read_text())
    if manifest["model_hashes"] != model_hashes(): raise RuntimeError("model changed")
    cases, x = _load("locked", workspace)
    if [c.case_id for c in cases] != manifest["locked_ids"]: raise RuntimeError("locked suite mismatch")
    started = time.perf_counter(); results = {}
    for name in ("linear", "projection"):
        rows = _predictions(name, _load_checkpoint(workspace, name, x.shape[1]), x, cases)
        results[name] = {"metrics": score(cases, rows), "predictions": [asdict(p) for p in rows]}
    elapsed = time.perf_counter() - started
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024 if sys.platform == "darwin" else 1024)
    selected = manifest["operational"]; metrics = results[selected]["metrics"]
    gates = metrics["relation_macro_f1"] >= .95 and metrics["direction_accuracy"] >= .98 and metrics["role_exact_accuracy"] >= .98 and metrics["scope_accuracy"] >= .98 and metrics["disposition_accuracy"] >= .95 and metrics["topology_agreement"] >= .98 and elapsed < 600 and rss < 4096
    advantage = results["projection"]["metrics"]["relation_macro_f1"] - results["linear"]["metrics"]["relation_macro_f1"] >= .15
    classification = ("G2.1-O-PASS" if gates else "G2.1-C") + (" / G2.1-R-PASS" if advantage else " / G2.1-R-NOT-DEMONSTRATED")
    result = {"classification": classification, "operational": selected, "methods": results, "runtime_seconds": elapsed, "peak_rss_mb": rss}
    _write(path, result)
    return result


def verify(workspace: Path) -> dict:
    manifest = json.loads((workspace / "frozen-manifest.json").read_text())
    sources = {str(p.relative_to(ROOT)): _sha(p) for p in sorted((ROOT / "src" / "topology_g21").glob("*.py"))}
    if sources != manifest["source_hashes"] or model_hashes() != manifest["model_hashes"]: raise RuntimeError("frozen artifacts changed")
    return {"ok": True, "classification": json.loads((workspace / "locked-results.json").read_text())["classification"]}
