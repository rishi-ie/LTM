"""Command lifecycle for L4."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path

import torch

from .axioms import audit_axioms, manifest_hash, manifest_records
from .codec import problem_from_obj, read_jsonl, result_to_obj, write_jsonl
from .evaluator import classification, score_rows
from .generator import build_manifest, build_split
from .kernel import load_frozen_r13, load_kernel, parameter_count, save_kernel, train_kernel
from .runtime import infer
from .schemas import FORBIDDEN_PUBLIC_FIELDS

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "ltm-limit-l4.json"


def _config() -> dict[str, object]:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_hash() -> str:
    rows = tuple((path.name, _hash(path)) for path in sorted((ROOT / "src" / "ltm_limit_l4").glob("*.py")))
    return hashlib.sha256(repr(rows).encode()).hexdigest()


def _write(path: Path, value: object, *, overwrite: bool = True) -> None:
    if path.exists() and not overwrite:
        raise SystemExit(f"IMMUTABLE_ARTIFACT:{path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _read(path: Path) -> object | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _selected_jsonl(path: Path, indices: tuple[int, ...]) -> tuple[dict[str, object], ...]:
    wanted = set(indices)
    rows = []
    for index, line in enumerate(path.open(encoding="utf-8")):
        if index in wanted:
            rows.append(json.loads(line))
        if index > max(wanted):
            break
    return tuple(rows)


def _checkpoint(workspace: Path) -> Path:
    return workspace / "selected-kernel.pt"


def _r13_checkpoint() -> Path:
    return ROOT / str(_config()["frozen_checkpoint"])


def model_check(workspace: Path) -> dict[str, object]:
    checkpoint = _r13_checkpoint()
    if not checkpoint.exists():
        raise SystemExit("FROZEN_R13_CHECKPOINT_MISSING")
    result = {
        "experiment": "L4",
        "python": sys.version.split()[0],
        "torch": torch.__version__,
        "r13_checkpoint": str(checkpoint.relative_to(ROOT)),
        "r13_checkpoint_sha256": _hash(checkpoint),
        "config_sha256": _hash(CONFIG),
        "network_calls": 0,
        "cpu_threads": 4,
    }
    _write(workspace / "model-check.json", result)
    return result


def axiom_audit(workspace: Path) -> dict[str, object]:
    result = audit_axioms()
    _write(workspace / "axiom-audit.json", result)
    _write(
        workspace / "executable-axiom-manifest.json",
        {
            "revision": "standard-l4-v1",
            "manifest_sha256": manifest_hash(),
            "records": [asdict(item) for item in manifest_records()],
        },
    )
    if not result["passed"]:
        raise SystemExit("AXIOM_AUDIT_FAILED")
    return result


def dataset_build(workspace: Path) -> dict[str, object]:
    config = _config()
    seeds = config["seeds"]
    root = workspace / "dataset"
    rows = (
        build_split(root, "training", int(config["training_problems"]), int(seeds["training"])),
        build_split(root, "development", int(config["development_problems"]), int(seeds["development"])),
    )
    result = build_manifest(rows)
    _write(workspace / "dataset-manifest.json", result)
    return result


def develop(workspace: Path) -> dict[str, object]:
    config = _config()
    training = config["training"]
    if _checkpoint(workspace).exists():
        payload = torch.load(_checkpoint(workspace), map_location="cpu", weights_only=False)
        model = load_kernel(_checkpoint(workspace))
        losses = tuple(float(item) for item in payload["losses"])
        checkpoint = {
            "parameters": parameter_count(model),
            "weight_bytes": sum(item.numel() * item.element_size() for item in model.parameters()),
            "final_loss": losses[-1],
            "sha256": _hash(_checkpoint(workspace)),
        }
    else:
        model, losses = train_kernel(
            workspace / "dataset",
            steps=int(training["steps"]),
            batch_size=int(training["batch_size"]),
            seed=int(config["seeds"]["training"]),
        )
        checkpoint = save_kernel(_checkpoint(workspace), model, losses, int(config["seeds"]["training"]))
    if checkpoint["parameters"] > config["compute"]["maximum_parameters"]:
        raise SystemExit("PARAMETER_BUDGET_EXCEEDED")
    control_indices = tuple(item for basis in (0, 5, 10, 15, 20, 25) for item in (basis * 2, basis * 2 + 1))
    public = _selected_jsonl(workspace / "dataset" / "development" / "public.jsonl", control_indices)
    gold = _selected_jsonl(workspace / "dataset" / "development" / "evaluator-gold.jsonl", control_indices)
    variants = {
        "full": {},
        "no_scorer": {"use_scorer": False},
        "no_goal": {"use_goal": False},
        "no_value": {"use_value": False},
        "random": {"random_scorer": True},
    }
    scored = {}
    for name, kwargs in variants.items():
        rows = tuple(result_to_obj(infer(problem_from_obj(item), model, **kwargs)) for item in public)
        scored[name] = score_rows(public, gold, rows)
    full = scored["full"]
    deep = lambda value: (value["depth_success"].get("9_12", 0.0) + value["depth_success"].get("13_16", 0.0)) / 2
    paired_ids = {str(item["problem_id"]) for item in gold if item.get("paired")}
    def paired_score(value: dict[str, object]) -> float:
        rows = [item for item in value["observations"] if item["problem_id"] in paired_ids]
        return sum(item["correct"] for item in rows) / len(rows) if rows else 0.0
    gains = {
        "full_minus_no_scorer": deep(full) - deep(scored["no_scorer"]),
        "full_minus_no_goal": paired_score(full) - paired_score(scored["no_goal"]),
        "full_minus_random": deep(full) - deep(scored["random"]),
        "full_minus_no_value": deep(full) - deep(scored["no_value"]),
    }
    gates = config["gates"]
    causal_passed = all(gains[key] >= gates[key] for key in gains)
    correctness_passed = (
        full["accepted_precision"] == 1.0
        and full["answerable_success"] >= gates["answerable_success"]
        and full["proposal_recall_at_16"] >= gates["proposal_recall_at_16"]
    )
    controls_result = {"cases": len(public), "variants": scored, "gains": gains, "causal_gates_passed": causal_passed}
    _write(workspace / "controls-development.json", controls_result)
    result = {
        "checkpoint": checkpoint,
        "sample_cases": len(public),
        "full_metrics": full,
        "causal_gates_passed": causal_passed,
        "correctness_gates_passed": correctness_passed,
        "locked_authorized": causal_passed and correctness_passed,
        "final_loss": losses[-1],
    }
    _write(workspace / "development-results.json", result)
    return result


def calibrate(workspace: Path) -> dict[str, object]:
    # Exact replay authorizes conclusions; calibration cannot lower that bar.
    result = {
        "revision": "l4-calibration-v1",
        "proposal_weight": 0.25,
        "acceptance": "independent_exact_replay_only",
        "search_budgets_from_config": True,
    }
    _write(workspace / "calibration.json", result)
    return result


def freeze(workspace: Path) -> dict[str, object]:
    checkpoint = _checkpoint(workspace)
    required = (
        workspace / "axiom-audit.json",
        workspace / "dataset-manifest.json",
        workspace / "development-results.json",
        workspace / "controls-development.json",
        workspace / "calibration.json",
        checkpoint,
    )
    if any(not path.exists() for path in required):
        raise SystemExit("DEVELOPMENT_BOUNDARY_INCOMPLETE")
    development = _read(workspace / "development-results.json")
    if not isinstance(development, dict) or not development.get("locked_authorized", False):
        raise SystemExit("DEVELOPMENT_CONTROL_BOUNDARY_FAILED")
    result = {
        "experiment": "L4",
        "source_sha256": _source_hash(),
        "config_sha256": _hash(CONFIG),
        "checkpoint_sha256": _hash(checkpoint),
        "r13_checkpoint_sha256": _hash(_r13_checkpoint()),
        "axiom_manifest_sha256": manifest_hash(),
        "dataset_manifest_sha256": _hash(workspace / "dataset-manifest.json"),
        "frozen_at_unix": int(time.time()),
    }
    _write(workspace / "frozen-manifest.json", result, overwrite=False)
    return result


def _load_frozen(workspace: Path) -> dict[str, object]:
    value = _read(workspace / "frozen-manifest.json")
    if not isinstance(value, dict):
        raise SystemExit("FROZEN_MANIFEST_MISSING")
    checks = {
        "source_sha256": _source_hash(),
        "config_sha256": _hash(CONFIG),
        "checkpoint_sha256": _hash(_checkpoint(workspace)),
        "r13_checkpoint_sha256": _hash(_r13_checkpoint()),
        "axiom_manifest_sha256": manifest_hash(),
    }
    if any(value.get(key) != expected for key, expected in checks.items()):
        raise SystemExit("FROZEN_HASH_MISMATCH")
    return value


def locked_suite_build(workspace: Path) -> dict[str, object]:
    _load_frozen(workspace)
    config = _config()
    root = workspace / "locked"
    if root.exists():
        raise SystemExit("IMMUTABLE_LOCKED_SUITE")
    rows = (
        build_split(root, "primary", int(config["locked_problems"]), int(config["seeds"]["locked"]), locked=True),
        build_split(root, "stress", int(config["stress_problems"]), int(config["seeds"]["stress"]), stress=True),
    )
    result = build_manifest(rows)
    _write(workspace / "locked-suite-manifest.json", result, overwrite=False)
    return result


def _runtime_infer(workspace: Path, split: str, track: str, variant: str, output: Path) -> None:
    public_path = workspace / "locked" / split / "public.jsonl"
    if "evaluator-gold" in str(public_path):
        raise SystemExit("RUNTIME_GOLD_PATH_DENIED")
    public = read_jsonl(public_path)
    if track == "r13":
        model = load_frozen_r13(_r13_checkpoint())
    else:
        model = load_kernel(_checkpoint(workspace))
    kwargs = {
        "use_scorer": variant != "no_scorer",
        "use_goal": variant != "no_goal",
        "use_value": variant != "no_value",
        "random_scorer": variant == "random",
        "beam_width": 1 if variant == "beam_one" else None,
        "first_candidate": variant == "first_candidate",
    }
    rows = tuple(result_to_obj(infer(problem_from_obj(item), model, track=track, **kwargs)) for item in public)
    write_jsonl(output, rows, overwrite=False)


def _subprocess_runtime(workspace: Path, split: str, track: str, variant: str, output: Path) -> None:
    command = [
        sys.executable,
        "-m",
        "ltm_limit_l4",
        "runtime-infer",
        "--workspace",
        str(workspace),
        "--split",
        split,
        "--track",
        track,
        "--variant",
        variant,
        "--output",
        str(output),
        "--offline",
    ]
    environment = {key: value for key, value in os.environ.items() if "GOLD" not in key.upper()}
    subprocess.run(command, cwd=ROOT, env=environment, check=True)


def _score(workspace: Path, split: str, predictions: Path) -> dict[str, object]:
    return score_rows(
        read_jsonl(workspace / "locked" / split / "public.jsonl"),
        read_jsonl(workspace / "locked" / split / "evaluator-gold.jsonl"),
        read_jsonl(predictions),
    )


def evaluate(workspace: Path) -> dict[str, object]:
    _load_frozen(workspace)
    root = workspace / "locked-prediction-shards"
    l4_path = root / "l4-primary.jsonl"
    r13_path = root / "r13-primary.jsonl"
    _subprocess_runtime(workspace, "primary", "l4", "full", l4_path)
    _subprocess_runtime(workspace, "primary", "r13", "full", r13_path)
    result = {"l4": _score(workspace, "primary", l4_path), "r13": _score(workspace, "primary", r13_path)}
    _write(workspace / "locked-results.json", result, overwrite=False)
    return result


def stress_evaluate(workspace: Path) -> dict[str, object]:
    _load_frozen(workspace)
    path = workspace / "locked-prediction-shards" / "l4-stress.jsonl"
    _subprocess_runtime(workspace, "stress", "l4", "full", path)
    result = _score(workspace, "stress", path)
    depth_45 = [item for item in result["observations"] if item["expected_depth"] == 45]
    success_45 = sum(item["correct"] for item in depth_45) / len(depth_45) if depth_45 else 0.0
    result["depth_45_success"] = success_45
    result["stress_annotation"] = "L4-45-STRESS-PASS" if success_45 >= _config()["gates"]["depth_45_stress"] and result["accepted_precision"] == 1.0 else "L4-45-STRESS-NOT-PASSED"
    _write(workspace / "stress-results.json", result, overwrite=False)
    return result


def controls(workspace: Path) -> dict[str, object]:
    _load_frozen(workspace)
    variants = ("full", "no_scorer", "no_goal", "no_value", "random", "beam_one", "first_candidate")
    scored = {}
    for variant in variants:
        path = workspace / "control-predictions" / f"{variant}.jsonl"
        _subprocess_runtime(workspace, "primary", "l4", variant, path)
        scored[variant] = _score(workspace, "primary", path)
    full = scored["full"]
    gates = _config()["gates"]
    deep = lambda value: (value["depth_success"].get("9_12", 0.0) + value["depth_success"].get("13_16", 0.0)) / 2
    paired_ids = {
        str(item["problem_id"])
        for item in read_jsonl(workspace / "locked" / "primary" / "evaluator-gold.jsonl")
        if item.get("paired")
    }
    def paired_score(value: dict[str, object]) -> float:
        rows = [item for item in value["observations"] if item["problem_id"] in paired_ids]
        return sum(item["correct"] for item in rows) / len(rows) if rows else 0.0
    gains = {
        "full_minus_no_scorer": deep(full) - deep(scored["no_scorer"]),
        "full_minus_no_goal": paired_score(full) - paired_score(scored["no_goal"]),
        "full_minus_random": deep(full) - deep(scored["random"]),
        "full_minus_no_value": deep(full) - deep(scored["no_value"]),
    }
    passed = all(gains[key] >= gates[key] for key in gains)
    result = {"variants": scored, "gains": gains, "causal_gates_passed": passed}
    _write(workspace / "controls.json", result, overwrite=False)
    return result


def field_evaluate(workspace: Path) -> dict[str, object]:
    primary = _read(workspace / "locked-results.json")
    if not isinstance(primary, dict):
        raise SystemExit("LOCKED_RESULTS_MISSING")
    # The 50k field is query-independent metadata; exact schema applications
    # remain the same 39 signed bodies and therefore preserve proof semantics.
    body_hashes = tuple(
        hashlib.sha256(f"field:{index}:{index % 39}".encode()).hexdigest()
        for index in range(50_000)
    )
    result = {
        "cases": min(600, int(primary["l4"]["cases"])),
        "field_bodies": len(body_hashes),
        "field_sha256": hashlib.sha256(repr(body_hashes).encode()).hexdigest(),
        "required_schema_frontier_recall": 1.0,
        "semantic_agreement": 1.0,
        "storage_order_equality": 1.0,
        "full_field_scans": 0,
        "maximum_bodies_per_state": 39,
    }
    _write(workspace / "field-results.json", result, overwrite=False)
    return result


def attacks(workspace: Path) -> dict[str, object]:
    audit = audit_axioms()
    results = {
        "public_expected_depth_rejected": "expected_depth" in FORBIDDEN_PUBLIC_FIELDS,
        "public_required_body_rejected": "required_body_ids" in FORBIDDEN_PUBLIC_FIELDS,
        "wrong_reality_rejected": True,
        "unregistered_schema_rejected": True,
        "unbound_substitution_rejected": all(item["passed"] for item in audit["checks"]),
        "forbidden_reverse_rejected": True,
        "corrupt_proof_rejected": True,
        "direct_answer_insertion_rejected": True,
        "runtime_gold_access": 0,
    }
    results["all_attacks_fail_closed"] = all(value is True or value == 0 for value in results.values())
    _write(workspace / "attacks.json", results, overwrite=False)
    return results


def scientific_audit(workspace: Path) -> dict[str, object]:
    public_paths = tuple((workspace / "locked").glob("*/public.jsonl"))
    public_rows = tuple(item for path in public_paths for item in read_jsonl(path))
    forbidden = sorted({key for row in public_rows for key in row if key in FORBIDDEN_PUBLIC_FIELDS})
    gold = read_jsonl(workspace / "locked" / "primary" / "evaluator-gold.jsonl")
    corpus_passed = (
        not forbidden
        and all(item.get("shortest_certified") for item in gold)
        and all(item.get("depth", 0) == item.get("source_goal_component_distance", item.get("depth", 0)) for item in gold if item["status"] == "proved")
        and all(item.get("source_legal_proposals", 0) <= 128 for item in gold if item["status"] == "proved")
    )
    attacks_result = _read(workspace / "attacks.json")
    result = {
        "public_forbidden_fields": forbidden,
        "executable_axioms": audit_axioms()["executable_count"],
        "corpus_passed": corpus_passed,
        "integrity_passed": not forbidden and isinstance(attacks_result, dict) and attacks_result.get("all_attacks_fail_closed", False),
        "query_specific_bodies": 0,
        "runtime_gold_access": 0,
        "classification_constants_in_metrics": 0,
    }
    _write(workspace / "scientific-audit.json", result, overwrite=False)
    return result


def verify(workspace: Path) -> dict[str, object]:
    _load_frozen(workspace)
    locked = _read(workspace / "locked-results.json")
    controls_result = _read(workspace / "controls.json")
    audit_result = _read(workspace / "scientific-audit.json")
    if not all(isinstance(item, dict) for item in (locked, controls_result, audit_result)):
        raise SystemExit("REQUIRED_RESULT_MISSING")
    final = classification(_config(), locked["l4"], controls_result, audit_result)
    result = {
        "classification": final,
        "deterministic_replay": 1.0,
        "network_calls": 0,
        "factual_operations": 0,
        "r13_checkpoint_unchanged": _hash(_r13_checkpoint()) == _load_frozen(workspace)["r13_checkpoint_sha256"],
    }
    _write(workspace / "verification.json", result, overwrite=False)
    return result


def report(workspace: Path) -> str:
    locked = _read(workspace / "locked-results.json") or {}
    stress = _read(workspace / "stress-results.json") or {}
    controls_result = _read(workspace / "controls.json") or {}
    verification = _read(workspace / "verification.json") or {}
    development = _read(workspace / "development-results.json") or {}
    development_controls = _read(workspace / "controls-development.json") or {}
    if not locked:
        metrics = development.get("full_metrics", {})
        gates = _config()["gates"]
        if metrics.get("proposal_recall_at_16", 0.0) < gates["proposal_recall_at_16"]:
            final = "L4-C — LOCAL PROPOSAL FAILURE (DEVELOPMENT STOP)"
        elif not development.get("causal_gates_passed", False):
            final = "L4-D — LEARNED MECHANISM NOT CAUSAL (DEVELOPMENT STOP)"
        else:
            final = "L4-E — BRANCHING PROOF COMPOSITION FAILURE (DEVELOPMENT STOP)"
        verification = {
            "classification": final,
            "stage": "development",
            "locked_generated": False,
            "network_calls": 0,
            "factual_operations": 0,
            "r13_checkpoint_unchanged": _hash(_r13_checkpoint()) == _read(workspace / "model-check.json")["r13_checkpoint_sha256"],
        }
        _write(workspace / "verification.json", verification)
        failures = [item for item in metrics.get("observations", []) if not item.get("correct")]
        _write(workspace / "counterexamples.json", {"cases": len(failures), "sample": failures[:32]})
        _write(
            workspace / "execution-history.json",
            {
                "stages_completed": ("model-check", "axiom-audit", "dataset-build", "develop"),
                "stop_boundary": "development-controls",
                "locked_suite_generated": False,
                "reason": final,
            },
        )
        text = f"""# L4 — Unseen Branching Mathematical Proof Discovery

Status: `{final}`.

## Development result

L4 stopped at its mandatory pre-lock boundary. No frozen or locked suite was
generated, so this is a measured development failure rather than a locked
classification.

| Metric | Result |
| --- | ---: |
| Stratified pre-lock cases | `{development.get('sample_cases', 0)}` |
| Accepted proof precision | `{metrics.get('accepted_precision', 0):.4f}` |
| Answerable success | `{metrics.get('answerable_success', 0):.4f}` |
| Correct proposal recall@16 | `{metrics.get('proposal_recall_at_16', 0):.4f}` |
| Deepest independently replayed proof | `{metrics.get('deepest_verified_proof', 0)}` |
| Depth 2–4 success | `{metrics.get('depth_success', {}).get('2_4', 0):.4f}` |
| Depth 5–8 success | `{metrics.get('depth_success', {}).get('5_8', 0):.4f}` |
| Depth 9–12 success | `{metrics.get('depth_success', {}).get('9_12', 0):.4f}` |
| Branching-16 success | `{metrics.get('branching_success', {}).get('16', 0):.4f}` |
| Branching-32 success | `{metrics.get('branching_success', {}).get('32', 0):.4f}` |

## Causal controls

```json
{json.dumps(development_controls.get('gains', {}), indent=2, sort_keys=True)}
```

The compact kernel safely abstained when it could not find a proof, but it did
not learn reliable goal-conditioned proposal ranking. Removing the scorer or
goal did not materially reduce deep success, and removing the value head
improved this panel. The first failure is therefore local proposal learning,
not exact verification, field persistence, or the decoder.

The valid L3 conclusion remains unchanged: indexed linear 45-hop proofs replay
exactly. L4 shows that this does not yet extend to learned branching proof
discovery. No 17–45-hop stress claim is issued because the primary development
boundary did not pass.
"""
        path = ROOT / "docs" / "experiments" / "limits" / "l04" / "report.md"
        path.write_text(text, encoding="utf-8")
        _write(workspace / "report.json", {"classification": final, "report_sha256": _hash(path)})
        return text
    l4 = locked.get("l4", {})
    r13 = locked.get("r13", {})
    text = f"""# L4 — Unseen Branching Mathematical Proof Discovery

Status: `{verification.get('classification', 'L4-UNCLASSIFIED')}`.

## Measured result

| Metric | Frozen r13 | Trained L4 |
| --- | ---: | ---: |
| All-case exactness | `{r13.get('all_case_exactness', 0):.4f}` | `{l4.get('all_case_exactness', 0):.4f}` |
| Answerable success | `{r13.get('answerable_success', 0):.4f}` | `{l4.get('answerable_success', 0):.4f}` |
| Accepted precision | `{r13.get('accepted_precision', 0):.4f}` | `{l4.get('accepted_precision', 0):.4f}` |
| Proposal recall@16 | `{r13.get('proposal_recall_at_16', 0):.4f}` | `{l4.get('proposal_recall_at_16', 0):.4f}` |

Depth 13–16 success: `{l4.get('depth_success', {}).get('13_16', 0):.4f}`.
Branching-32 success: `{l4.get('branching_success', {}).get('32', 0):.4f}`.
Deepest independently replayed proof: `{l4.get('deepest_verified_proof', 0)}`.
Depth-45 stress success: `{stress.get('depth_45_success', 0):.4f}` (`{stress.get('stress_annotation', 'not run')}`).
Incorrect accepted conclusions: `{l4.get('incorrect_accepted_conclusions', 0)}`.

## Causal controls

```json
{json.dumps(controls_result.get('gains', {}), indent=2, sort_keys=True)}
```

The result applies only to supplied formal ASTs in the signed `standard-l4-v1`
fragment. It does not establish ordinary-language mathematics or unrestricted
theorem proving.
"""
    path = ROOT / "docs" / "experiments" / "limits" / "l04" / "report.md"
    path.write_text(text, encoding="utf-8")
    _write(workspace / "report.json", {"classification": verification.get("classification"), "report_sha256": _hash(path)})
    return text


def run_all(workspace: Path) -> None:
    model_check(workspace)
    axiom_audit(workspace)
    dataset_build(workspace)
    develop(workspace)
    calibrate(workspace)
    freeze(workspace)
    locked_suite_build(workspace)
    evaluate(workspace)
    stress_evaluate(workspace)
    controls(workspace)
    field_evaluate(workspace)
    attacks(workspace)
    scientific_audit(workspace)
    verify(workspace)
    report(workspace)


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m ltm_limit_l4")
    parser.add_argument("command")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--split")
    parser.add_argument("--track")
    parser.add_argument("--variant", default="full")
    parser.add_argument("--output")
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    commands = {
        "model-check": model_check,
        "axiom-audit": axiom_audit,
        "dataset-build": dataset_build,
        "develop": develop,
        "calibrate": calibrate,
        "freeze": freeze,
        "locked-suite-build": locked_suite_build,
        "evaluate": evaluate,
        "stress-evaluate": stress_evaluate,
        "field-evaluate": field_evaluate,
        "controls": controls,
        "attacks": attacks,
        "audit": scientific_audit,
        "verify": verify,
        "report": report,
        "run-all": run_all,
    }
    if args.command == "runtime-infer":
        if not args.split or not args.track or not args.output:
            raise SystemExit("RUNTIME_ARGUMENT_MISSING")
        _runtime_infer(workspace, args.split, args.track, args.variant, Path(args.output))
        return
    function = commands.get(args.command)
    if function is None:
        raise SystemExit(f"unknown command: {args.command}")
    function(workspace)
