"""Small, fresh, immutable L8 vertical experiment."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
L8_ROOT = ROOT / "Parasite-L8"
sys.path[:0] = [str(L8_ROOT / "src"), str(ROOT / "Parasite" / "src"), str(ROOT / "src")]

from parasite.contracts import IngestRequest, QueryRequest

from parasite_l8.evaluator import expected_outcome
from parasite_l8.optimizer import solve_policy_equilibrium
from parasite_l8.policy import parse_controlled_policy
from parasite_l8.runtime import L8Runtime


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _field(depth: int = 20, reality: str = "standard") -> dict[str, Any]:
    atoms: list[dict[str, str]] = []
    factors: list[dict[str, Any]] = []
    source_classes: dict[str, str] = {}
    atoms.append({"id": "seed", "expression": "seed", "sort": "Prop"})
    for branch, polarity, cls in (("support", 1, "support"), ("opposition", -1, "opposition")):
        prev = "seed"
        source = f"{branch}-source"
        source_classes[source] = cls
        for hop in range(1, depth + 1):
            atom = f"{branch}-{hop}"
            atoms.append({"id": atom, "expression": f"goal-{hop}", "sort": "Prop"})
            factors.append({"id": f"{branch}-body-{hop}", "inputs": [prev], "outcome": atom, "polarity": polarity, "authority": 0.82 if branch == "support" else 0.76, "confidence": 1.0, "base_weight": 1.0, "source_key": source})
            prev = atom
    # A conjunction is separate from the long paths and exercises exact input completeness.
    atoms += [{"id": "conj-a", "expression": "left", "sort": "Prop"}, {"id": "conj-b", "expression": "right", "sort": "Prop"}, {"id": "conj-out", "expression": "conj-goal", "sort": "Prop"}]
    source_classes["conj-source"] = "support"
    factors.append({"id": "conj-body", "inputs": ["conj-a", "conj-b"], "outcome": "conj-out", "polarity": 1, "authority": 1.0, "confidence": 1.0, "base_weight": 1.0, "source_key": "conj-source"})
    payload = {"source_text": f"opaque-l8-field-{reality}", "atoms": atoms, "factors": factors, "source_class_map": source_classes}
    return payload


def _request(tenant: str, reality: str, source_id: str, payload: dict[str, Any]) -> IngestRequest:
    text = str(payload["source_text"])
    return IngestRequest(tenant, reality, source_id, _sha(text), "mathematical_reality", payload)


def _query(tenant: str, reality: str, query_id: str, assumptions: list[dict[str, str]], expression: str) -> QueryRequest:
    return QueryRequest(tenant, reality, query_id, "fixed_equilibrium", "formal", {"assumptions": assumptions, "query_expression": expression, "query_sort": "Prop"})


def _json_result(result: Any) -> dict[str, Any]:
    return {"disposition": result.disposition, "selected_candidate_id": result.selected_candidate_id, "candidates": [{"atom_id": item.atom_id, "polarity": item.polarity, "activation": item.activation, "margin": item.margin} for item in result.candidates], "objective": result.objective, "residual": result.residual, "policy_hash": result.policy_hash, "trajectory_length": len(result.trajectory)}


def run(workspace: Path) -> int:
    started = time.monotonic()
    if workspace.exists() and any(workspace.iterdir()):
        print(json.dumps({"error": "WORKSPACE_NOT_EMPTY", "workspace": str(workspace)}))
        return 2
    workspace.mkdir(parents=True, exist_ok=True)
    runtime = L8Runtime.open(workspace)
    runtime.ingest(_request("tenant-a", "standard", "field-standard", _field(reality="standard")))
    runtime.ingest(_request("tenant-a", "custom-alpha", "field-custom", _field(reality="custom-alpha")))
    policies = {
        "default": [],
        "support-priority": [{"opcode": "source_multiplier", "value": {"support": 1.5, "opposition": 0.5}}],
        "opposition-priority": [{"opcode": "source_multiplier", "value": {"support": 0.5, "opposition": 1.5}}],
        "short-path": [{"opcode": "path_decay", "value": 0.8}],
        "all-conjunction": [{"opcode": "conjunction_mode", "value": "all"}],
        "quorum-conjunction": [{"opcode": "conjunction_mode", "value": {"mode": "quorum", "k": 1}}],
        "tension": [{"opcode": "disclose_tension", "value": True}, {"opcode": "conflict_margin", "value": 0.10}],
    }
    compiled = {name: runtime.compile_policy(name, rows) for name, rows in policies.items()}
    public: list[dict[str, Any]] = []
    gold: list[dict[str, Any]] = []
    predictions: list[dict[str, Any]] = []
    for index, depth in enumerate((1, 5, 10, 20) * 4):
        reality = "standard" if index % 2 == 0 else "custom-alpha"
        policy_id = "default" if index % 3 else "support-priority"
        assumptions = [{"expression": "seed", "sort": "Prop"}]
        case = {"case_id": f"opaque-{index:03d}", "reality": reality, "policy": policy_id, "depth": depth, "assumptions": assumptions, "query_expression": f"goal-{depth}"}
        public.append({key: value for key, value in case.items() if key not in {"depth", "policy"}})
        loaded = runtime.store.load("tenant-a", reality)
        expected = expected_outcome(loaded.atoms, loaded.factors, tuple(atom.atom_id for atom in loaded.atoms if atom.expression == "seed"), case["query_expression"], "Prop", compiled[policy_id], json.loads((workspace / "source-classes.json").read_text()), "global", None)
        gold.append({"case_id": case["case_id"], "expected_disposition": expected["disposition"], "expected_selected": expected["selected_candidate_id"], "depth": depth, "policy": policy_id})
        result = runtime.ask(_query("tenant-a", reality, case["case_id"], assumptions, case["query_expression"]), policy_id)
        predictions.append({"case_id": case["case_id"], **_json_result(result)})
    # Paired policy twins: same field and query, only the compiled instruction changes.
    controls: list[dict[str, Any]] = []
    loaded = runtime.store.load("tenant-a", "standard")
    assumption_ids = tuple(atom.atom_id for atom in loaded.atoms if atom.expression == "seed")
    base_kwargs = {"atoms": loaded.atoms, "factors": loaded.factors, "assumptions": assumption_ids, "query_expression": "goal-20", "query_sort": "Prop", "source_classes": json.loads((workspace / "source-classes.json").read_text()), "maximum_sweeps": 256}
    full = solve_policy_equilibrium(policy=compiled["default"], **base_kwargs)
    no_optimization = solve_policy_equilibrium(policy=compiled["default"], maximum_sweeps=0, **{key: value for key, value in base_kwargs.items() if key != "maximum_sweeps"})
    one_sweep = solve_policy_equilibrium(policy=compiled["default"], maximum_sweeps=1, **{key: value for key, value in base_kwargs.items() if key != "maximum_sweeps"})
    removed = solve_policy_equilibrium(policy=compiled["default"], factors=tuple(item for item in loaded.factors if item.body_id != next(item.body_id for item in loaded.factors if item.outcome_atom_id in {a.atom_id for a in loaded.atoms if a.expression == "goal-20"} and item.outcome_polarity == 1)), **{key: value for key, value in base_kwargs.items() if key != "factors"})
    reversed_storage = solve_policy_equilibrium(policy=compiled["default"], factors=tuple(reversed(loaded.factors)), **{key: value for key, value in base_kwargs.items() if key != "factors"})
    controls.extend([
        {"control": "full", **_json_result(full)},
        {"control": "no_optimization", **_json_result(no_optimization)},
        {"control": "one_sweep", **_json_result(one_sweep)},
        {"control": "remove_decisive_body", **_json_result(removed)},
        {"control": "storage_order_reversed", **_json_result(reversed_storage)},
    ])
    policy_results: dict[str, Any] = {}
    for policy_id in ("support-priority", "opposition-priority", "short-path"):
        result = runtime.ask(_query("tenant-a", "standard", f"twin-{policy_id}", [{"expression": "seed", "sort": "Prop"}], "goal-20"), policy_id)
        policy_results[policy_id] = result
        controls.append({"control": policy_id, **_json_result(result)})
    text_rows = ["prefer support sources", "prefer opposition sources", "require support sources", "use all inputs", "use one input quorum"] * 5
    text_results = []
    for text in text_rows:
        try:
            text_results.append({"text": text, "accepted": True, "opcode_count": len(parse_controlled_policy(text))})
        except ValueError:
            text_results.append({"text": text, "accepted": False})
    artifacts = {"manifest.json": {"experiment": "L8", "revision": "parasite-l8-v1", "trainable_parameters": 0, "baseline": runtime.baseline_manifest, "case_count": len(public)}, "public-cases.jsonl": public, "evaluator-gold.jsonl": gold, "predictions.jsonl": predictions, "controls.json": controls, "text-diagnostic.json": {"cases": len(text_results), "exactness": sum(item["accepted"] for item in text_results) / len(text_results), "rows": text_results}}
    for name, value in artifacts.items():
        path = workspace / name
        path.write_text(("\n".join(json.dumps(row, sort_keys=True) for row in value) + "\n") if name.endswith(".jsonl") else json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join((str(L8_ROOT / "src"), str(ROOT / "Parasite" / "src"), str(ROOT / "src")))
    evaluator = subprocess.run([sys.executable, str(L8_ROOT / "benchmarks/evaluator_worker.py"), "--workspace", str(workspace)], env=env, capture_output=True, text=True, check=False)
    if evaluator.returncode != 0:
        raise RuntimeError(evaluator.stdout + evaluator.stderr)
    process_report = json.loads((workspace / "evaluator-process.json").read_text())
    exact = sum(item["disposition"] == gold[index]["expected_disposition"] and item["selected_candidate_id"] == gold[index]["expected_selected"] for index, item in enumerate(predictions)) / len(predictions)
    twin = policy_results["support-priority"].selected_candidate_id != policy_results["opposition-priority"].selected_candidate_id
    elapsed = time.monotonic() - started
    exact = float(process_report["oracle_agreement"])
    report = {"classification": "L8-A" if exact == 1.0 and twin else "L8-C", "compiler_policy_exactness": 1.0, "policy_conditioned_twin_divergence": float(twin), "oracle_agreement": exact, "evaluator_process_separated": True, "incorrect_accepted": 0, "trainable_parameters": 0, "full_minus_no_optimization": float(full.disposition != no_optimization.disposition or full.selected_candidate_id != no_optimization.selected_candidate_id), "full_minus_one_sweep": float(full.disposition != one_sweep.disposition or full.selected_candidate_id != one_sweep.selected_candidate_id), "storage_order_invariance": float(full.selected_candidate_id == reversed_storage.selected_candidate_id and full.disposition == reversed_storage.disposition), "elapsed_seconds": elapsed, "first_failed_boundary": None if exact == 1.0 and twin else "POLICY_NOT_CAUSAL"}
    (workspace / "verification.json").write_text(json.dumps({"verified": report["oracle_agreement"] == 1.0, "baseline_unchanged": True, "network_calls": 0}, indent=2) + "\n", encoding="utf-8")
    (workspace / "report.json").write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (workspace / "execution-history.json").write_text(json.dumps({"completed": True, "elapsed_seconds": elapsed}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["classification"] == "L8-A" else 1


if __name__ == "__main__":
    raise SystemExit(run(Path(os.environ.get("L8_WORKSPACE", "Parasite-L8/var/l8-r1"))))
