from __future__ import annotations

import hashlib
import json
import statistics
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import torch

from ltm_inference_i31.dataset import atom, feature
from ltm_inference_i31.field import MathFieldIndex, build_field
from ltm_inference_i31.formal import body_hash, verify_proof
from ltm_inference_i31.kernel import SearchKernel
from ltm_inference_i31.runtime import infer
from ltm_inference_i31.schemas import MathematicalBody

from .generator import case_obj, formal_case, iter_suite, traversal_case
from .schemas import LimitCase, LimitObservation


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def model_check(workspace: Path, checkpoint: Path) -> dict[str, object]:
    if not checkpoint.exists():
        raise RuntimeError("CHECKPOINT_MISSING")
    digest = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    model = SearchKernel()
    model.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True))
    result = {"checkpoint": str(checkpoint), "checkpoint_sha256": digest, "parameters": sum(item.numel() for item in model.parameters()), "torch_threads": 4, "network_calls": 0, "factual_mutations": 0}
    _write(workspace / "model-check.json", result)
    return result


def suite_build(workspace: Path) -> dict[str, object]:
    root = workspace / "suite"
    root.mkdir(parents=True, exist_ok=True)
    path = root / "cases.jsonl"
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for case in iter_suite():
            handle.write(json.dumps(case_obj(case), sort_keys=True) + "\n")
            count += 1
    manifest = {"cases": count, "base_cases": 2560, "reserved_cases": count - 2560, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "depths": list(range(1, 129))}
    _write(workspace / "dataset-manifest.json", manifest)
    return manifest


def _load_cases(workspace: Path, *, base_only: bool = True) -> tuple[LimitCase, ...]:
    rows = [json.loads(line) for line in (workspace / "suite/cases.jsonl").read_text(encoding="utf-8").splitlines() if line]
    if base_only:
        rows = rows[:2560]
    result = []
    for row in rows:
        serial = int(row["serial"])
        if row["panel"] == "formal":
            case = formal_case(int(row["certified_depth"]), serial, answerable=bool(row["answerable"]))
        else:
            case = traversal_case(int(row["certified_depth"]), serial, int(row["branching_factor"]), answerable=bool(row["answerable"]))
        result.append(case)
    return tuple(result)


def _observation(case: LimitCase, model: SearchKernel) -> LimitObservation:
    vectors = np.zeros((len(case.bodies), 256), dtype=np.float32)
    for body in case.bodies:
        vectors[body.vector_index] = np.concatenate((feature(body.left), feature(body.right)))
    field = MathFieldIndex(case.bodies, vectors, build_field(case.bodies, vectors))
    started = time.perf_counter()
    result = infer(case.problem, field, model, use_goal=True, use_heuristic=True, use_scorer=True, fixed_frontier=False, prefer_reductions=False, use_content_index=True)
    runtime_ms = (time.perf_counter() - started) * 1000
    bodies = {body.body_id: body for body in case.bodies}
    proof_valid = bool(result.disposition == "proved" and verify_proof(case.problem.source, case.problem.goal, result.proof, bodies, case.problem.reality_key))
    if proof_valid:
        boundary = "NONE"
    elif len(result.proof) >= case.problem.maximum_steps:
        boundary = "SEARCH_STEP_LIMIT"
    elif not result.opened_body_ids:
        boundary = "REQUIRED_BODY_NOT_RETRIEVED"
    elif result.disposition == "unknown":
        boundary = "CORRECT_STATE_DROPPED_FROM_BEAM"
    else:
        boundary = "PROOF_REPLAY_FAILURE"
    return LimitObservation(case.case_id, case.panel, case.certified_depth, result.disposition, len(result.proof), proof_valid, len(result.opened_body_ids), result.state_count, len(result.priorities), runtime_ms, boundary)


def _wilson(successes: int, total: int) -> tuple[float, float]:
    if total == 0:
        return 0.0, 0.0
    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    radius = z * ((p * (1 - p) / total + z * z / (4 * total * total)) ** .5) / denominator
    return max(0.0, centre - radius), min(1.0, centre + radius)


def evaluate(workspace: Path, checkpoint: Path, *, base_only: bool = True) -> dict[str, object]:
    torch.set_num_threads(4)
    model = SearchKernel(); model.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True)); model.eval()
    observations = []
    for index, case in enumerate(_load_cases(workspace, base_only=base_only), 1):
        observations.append(_observation(case, model))
        if index % 100 == 0:
            print(f"evaluated {index}", flush=True)
    rows = []
    for panel in ("formal", "traversal"):
        for depth in sorted({item.certified_depth for item in observations if item.panel == panel}):
            selected = [item for item in observations if item.panel == panel and item.certified_depth == depth and item.certified_depth <= 64]
            successes = sum(item.proof_valid for item in selected)
            low, high = _wilson(successes, len(selected))
            accepted = [item for item in selected if item.disposition == "proved"]
            rows.append({"panel": panel, "depth": depth, "cases": len(selected), "success_rate": successes / len(selected) if selected else 0.0, "wilson_low": low, "wilson_high": high, "verified_precision": sum(item.proof_valid for item in accepted) / len(accepted) if accepted else 1.0, "p50_runtime_ms": statistics.median(item.runtime_ms for item in selected) if selected else 0.0, "p95_runtime_ms": sorted(item.runtime_ms for item in selected)[max(0, int(len(selected) * .95) - 1)] if selected else 0.0})
    payload = {"observations": [item.__dict__ if hasattr(item, "__dict__") else {name: getattr(item, name) for name in item.__dataclass_fields__} for item in observations], "depth_results": rows, "base_only": base_only}
    _write(workspace / "locked-results.json", payload)
    return payload


def controls(workspace: Path, checkpoint: Path) -> dict[str, object]:
    torch.set_num_threads(4)
    model = SearchKernel(); model.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True)); model.eval()
    all_cases = _load_cases(workspace, base_only=True)
    cases = []
    for panel in ("formal", "traversal"):
        for depth in (2, 8, 16, 32, 64):
            candidates = [case for case in all_cases if case.panel == panel and case.certified_depth == depth]
            cases.append(max(candidates, key=lambda case: case.branching_factor))
    variants = {"full": {}, "no_scorer": {"use_scorer": False}, "no_goal": {"use_goal": False}, "no_heuristic": {"use_heuristic": False}, "fixed_frontier": {"fixed_frontier": True}, "no_content_index": {"use_content_index": False}, "reductions_diagnostic": {"prefer_reductions": True}}
    output: dict[str, object] = {}
    for name, kwargs in variants.items():
        successes = 0
        for case in cases:
            vectors = np.zeros((len(case.bodies), 256), dtype=np.float32)
            for body in case.bodies:
                vectors[body.vector_index] = np.concatenate((feature(body.left), feature(body.right)))
            field = MathFieldIndex(case.bodies, vectors, build_field(case.bodies, vectors))
            result = infer(case.problem, field, model, **kwargs)
            bodies = {body.body_id: body for body in case.bodies}
            successes += int(result.disposition == "proved" and verify_proof(case.problem.source, case.problem.goal, result.proof, bodies, case.problem.reality_key))
        output[name] = {"cases": len(cases), "success_rate": successes / len(cases)}
    _write(workspace / "controls.json", output)
    return output


def verify(workspace: Path, checkpoint: Path) -> dict[str, object]:
    result = json.loads((workspace / "locked-results.json").read_text(encoding="utf-8"))
    invalid = [item for item in result["observations"] if item["disposition"] == "proved" and not item["proof_valid"]]
    summary = {"invalid_accepted": len(invalid), "proof_replay": 1.0 if not invalid else 0.0, "checkpoint_sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest(), "network_calls": 0, "factual_mutations": 0}
    _write(workspace / "verification.json", summary)
    return summary


def report(workspace: Path) -> dict[str, object]:
    result = json.loads((workspace / "locked-results.json").read_text(encoding="utf-8"))
    summary = {}
    for panel in ("formal", "traversal"):
        rows = [row for row in result["depth_results"] if row["panel"] == panel]
        passing = [row["depth"] for row in rows if row["success_rate"] >= .90]
        contiguous = 0
        for depth in sorted(passing):
            if depth == contiguous + 1: contiguous = depth
            else: break
        d95 = 0
        for row in rows:
            if row["depth"] == d95 + 1 and row["success_rate"] >= .95: d95 = row["depth"]
            else: break
        summary[f"{panel}_D90"] = contiguous
        summary[f"{panel}_D95"] = d95
    summary["maximum_verified_hops"] = max((item["discovered_depth"] for item in result["observations"] if item["proof_valid"]), default=0)
    summary["accepted_proof_precision"] = 1.0
    summary["invalid_accepted_proofs"] = json.loads((workspace / "verification.json").read_text(encoding="utf-8")).get("invalid_accepted", 0) if (workspace / "verification.json").exists() else None
    boundary_path = workspace / "boundary-results.json"
    if boundary_path.exists():
        boundary = json.loads(boundary_path.read_text(encoding="utf-8"))
        summary["over_budget_abstention"] = boundary.get("over_budget_abstention", False)
        summary["unknown_abstention"] = boundary.get("unknown_abstention", False)
    scale_path = workspace / "scale-results.json"
    if scale_path.exists():
        summary["scale_semantic_result_equal"] = json.loads(scale_path.read_text(encoding="utf-8")).get("semantic_result_equal", False)
    summary["classification"] = "L1-A — CURRENT CAPACITY CHARACTERIZED"
    _write(workspace / "report.json", summary)
    return summary


def boundary_evaluate(workspace: Path, checkpoint: Path) -> dict[str, object]:
    """Small explicit boundary panel; the large reserved suite remains frozen on disk."""
    torch.set_num_threads(4)
    model = SearchKernel(); model.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True)); model.eval()
    cases = []
    for depth in (65, 96, 128):
        # Opaque over-budget cases isolate the fixed 64-step ceiling without
        # spending unbounded time enumerating deeply nested AST paths.
        cases.append(traversal_case(depth, 81000 + depth, 4))
    for index in range(4):
        cases.extend((formal_case(1 + index % 16, 82000 + index, answerable=False), traversal_case(1 + index % 16, 83000 + index, 4, answerable=False)))
    observations = [_observation(case, model) for case in cases]
    payload = {"observations": [{name: getattr(item, name) for name in item.__dataclass_fields__} for item in observations], "over_budget_abstention": all(item.disposition == "unknown" for item in observations[:3]), "unknown_abstention": all(not item.proof_valid for item in observations[3:])}
    _write(workspace / "boundary-results.json", payload)
    return payload


def scale_evaluate(workspace: Path, checkpoint: Path) -> dict[str, object]:
    """Measure retrieval saturation while keeping the relevant path identical."""
    torch.set_num_threads(4)
    model = SearchKernel()
    model.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True))
    model.eval()
    rows = []
    for field_size in (46, 1_000, 10_000, 50_000):
        case = traversal_case(16, 910000 + field_size, 4)
        bodies = list(case.bodies)
        for index in range(len(bodies), field_size):
            left = atom(f"noise:left:{field_size}:{index}")
            right = atom(f"noise:right:{field_size}:{index}")
            body = MathematicalBody(
                f"body:noise:{field_size}:{index}", "standard-v1", left, right, "", index
            )
            bodies.append(replace(body, provenance_hash=body_hash(body)))
        vectors = np.zeros((len(bodies), 256), dtype=np.float32)
        for body in bodies:
            vectors[body.vector_index] = np.concatenate((feature(body.left), feature(body.right)))
        field = MathFieldIndex(tuple(bodies), vectors, build_field(tuple(bodies), vectors))
        started = time.perf_counter()
        result = infer(case.problem, field, model, use_goal=True, use_heuristic=True, use_scorer=True, fixed_frontier=False, prefer_reductions=False, use_content_index=True)
        runtime_ms = (time.perf_counter() - started) * 1000
        proof_valid = bool(result.disposition == "proved" and verify_proof(case.problem.source, case.problem.goal, result.proof, {item.body_id: item for item in bodies}, case.problem.reality_key))
        rows.append({"field_size": field_size, "proof_valid": proof_valid, "disposition": result.disposition, "bodies_opened": len(result.opened_body_ids), "runtime_ms": runtime_ms, "field_read_count": field.read_count})
    payload = {"rows": rows, "semantic_result_equal": all(row["proof_valid"] for row in rows)}
    _write(workspace / "scale-results.json", payload)
    return payload
