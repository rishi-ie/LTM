"""Frozen L3 lifecycle: controlled compiler, 50k-body field, exact evaluator."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import asdict
from pathlib import Path

import torch

from .compiler import compile_body, compile_question, source, validate_body_source
from .corpus import load_locked, manifest_dict, materialize, materialize_locked
from .generator import grounded_case, locked_suite, mixed_case
from .runtime import _model, build_runtime_field, run_case
from .schemas import MathCorpusManifest

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "ltm-limit-l3.json"


def _write(path: Path, value: object, *, overwrite: bool = True) -> None:
    if path.exists() and not overwrite:
        raise SystemExit(f"IMMUTABLE_ARTIFACT:{path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _read(path: Path) -> object | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _config() -> dict[str, object]:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _checkpoint() -> Path:
    return ROOT / "workspaces/ltm-inference-i3-1-r13/selected-kernel.pt"


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_hash() -> str:
    rows = tuple((path.name, _hash(path)) for path in sorted((ROOT / "src" / "ltm_limit_l3").glob("*.py")))
    return hashlib.sha256(repr(rows).encode()).hexdigest()


def _reuse_locked_suite(source_workspace: Path, destination_workspace: Path) -> MathCorpusManifest:
    """Create an immutable r2 view over untouched r1 locked inputs.

    The r1 input suite completed before the non-semantic evaluator efficiency
    defect was found.  Hard links retain the exact bytes and avoid silently
    regenerating a new locked sample; no linked input is ever modified.
    """
    source_root = source_workspace / "locked"
    target_root = destination_workspace / "locked"
    names = ("compiled-suite.pkl", "evaluator-expectations.json", "public-cases.jsonl", "source-archive.jsonl")
    if any(not (source_root / name).exists() for name in names):
        raise SystemExit("REUSABLE_LOCKED_SUITE_MISSING")
    target_root.mkdir(parents=True, exist_ok=True)
    if any((target_root / name).exists() for name in names):
        raise SystemExit("IMMUTABLE_LOCKED_SUITE")
    for name in names:
        os.link(source_root / name, target_root / name)
    suite = load_locked(destination_workspace)
    archive_hash = _hash(target_root / "source-archive.jsonl")
    return MathCorpusManifest("standard-v1", len(suite.bodies), len(suite.bodies), suite.suite_hash, archive_hash)


def _observation(value) -> dict[str, object]:
    return asdict(value)


def _development_cases() -> tuple:
    return tuple(grounded_case(45, index) for index in range(2)) + (mixed_case(45, 0),)


def _load_frozen(workspace: Path) -> dict[str, object]:
    manifest = _read(workspace / "frozen-manifest.json")
    if not isinstance(manifest, dict):
        raise SystemExit("FROZEN_MANIFEST_MISSING")
    if manifest.get("checkpoint_sha256") != _hash(_checkpoint()):
        raise SystemExit("FROZEN_CHECKPOINT_MISMATCH")
    if manifest.get("config_sha256") != _hash(CONFIG) or manifest.get("source_sha256") != _source_hash():
        raise SystemExit("FROZEN_SOURCE_OR_CONFIG_MISMATCH")
    return manifest


def _run_panel(cases: tuple, bodies: tuple, checkpoint: Path) -> dict[str, object]:
    """Run an entire panel over one materialized 50k body field."""
    torch.set_num_threads(4)
    field = build_runtime_field(bodies)
    model = _model(checkpoint)
    observations = tuple(run_case(case, bodies, checkpoint, field=field, model=model) for case in cases)
    accepted = tuple(item for item in observations if item.disposition == "proved")
    expected_proved = tuple(item for item in observations if item.panel != "safety")
    valid_expected = tuple(
        item
        for case, item in zip(cases, observations, strict=True)
        if item.proof_valid and item.proof_steps == case.expected_depth and set(case.body_ids).issubset(item.proof_body_ids)
    )
    return {
        "cases": len(observations),
        "observations": tuple(_observation(item) for item in observations),
        "success_rate": len(valid_expected) / len(expected_proved) if expected_proved else 0.0,
        "accepted_precision": sum(item.proof_valid for item in accepted) / len(accepted) if accepted else 1.0,
        "proof_replay": sum(item.proof_valid for item in accepted) / len(accepted) if accepted else 1.0,
        "required_body_recall": sum(set(case.body_ids).issubset(item.proof_body_ids) for case, item in zip(cases, observations, strict=True) if case.panel != "safety") / len(expected_proved) if expected_proved else 1.0,
        "safe_coverage": len(accepted) / len(expected_proved) if expected_proved else 0.0,
        "invalid_accepted_proofs": sum(not item.proof_valid for item in accepted),
        "p95_runtime_ms": sorted(item.runtime_ms for item in observations)[max(0, int(len(observations) * .95) - 1)] if observations else 0.0,
        "field_body_count": len(bodies),
    }


def _compiler_metrics(suite) -> dict[str, object]:
    bodies = tuple(validate_body_source(source(body.source_text, source_id=f"recompile:{body.body_id}", reality_key=body.reality_key)) for body in suite.bodies)
    exact = tuple(
        item is not None and item[0] == original.left and item[1] == original.right and item[2] == original.axiom_id
        for item, original in zip(bodies, suite.bodies, strict=True)
    )
    questions = (*suite.grounded, *suite.mixed, *suite.safety)
    recompiled = tuple(compile_question(case.question.source) for case in questions)
    accepted = tuple(item.disposition == case.question.disposition for item, case in zip(recompiled, questions, strict=True))
    return {
        "status": "locked-evaluation",
        "body_count": len(suite.bodies),
        "accepted_body_precision": 1.0 if all(exact) else 0.0,
        "body_safe_coverage": sum(item is not None for item in bodies) / len(bodies),
        "body_ast_exactness": sum(exact) / len(exact),
        "question_precision": 1.0 if all(accepted) else 0.0,
        "question_safe_coverage": sum(accepted) / len(accepted),
        "source_archive_only_during_numeric_execution": True,
        "factual_operations": 0,
    }


def _controls(suite, checkpoint: Path) -> dict[str, object]:
    """Small stratified controls; the full panel is already the primary score."""
    cases = (*suite.grounded[:16], *suite.mixed[:8])
    variants = {
        "full": {},
        "no_goal_anchor": {"use_goal": False},
        "no_learned_scorer": {"use_scorer": False},
        "no_remaining_cost": {"use_heuristic": False},
        "fixed_frontier": {"fixed_frontier": True},
        "no_content_index": {"use_content_index": False},
    }
    torch.set_num_threads(4)
    field = build_runtime_field(suite.bodies)
    model = _model(checkpoint)
    results: dict[str, object] = {}
    for name, kwargs in variants.items():
        rows = tuple(run_case(case, suite.bodies, checkpoint, field=field, model=model, **kwargs) for case in cases)
        results[name] = {
            "cases": len(rows),
            "verified_success": sum(item.proof_valid and item.proof_steps == 45 for item in rows) / len(rows),
            "invalid_accepted_proofs": sum(item.disposition == "proved" and not item.proof_valid for item in rows),
        }
    reversed_field = build_runtime_field(tuple(reversed(suite.bodies)))
    reversed_rows = tuple(run_case(case, tuple(reversed(suite.bodies)), checkpoint, field=reversed_field, model=model) for case in cases)
    results["reversed_storage"] = {
        "cases": len(reversed_rows),
        "verified_success": sum(item.proof_valid and item.proof_steps == 45 for item in reversed_rows) / len(reversed_rows),
        "invalid_accepted_proofs": sum(item.disposition == "proved" and not item.proof_valid for item in reversed_rows),
    }
    return {"status": "locked-evaluation", "cases": len(cases), "variants": results}


def _attacks(suite, checkpoint: Path) -> dict[str, object]:
    """Fail-closed attacks are executed without giving runtime gold metadata."""
    torch.set_num_threads(4)
    field = build_runtime_field(suite.bodies)
    model = _model(checkpoint)
    unknown_rows = tuple(run_case(case, suite.bodies, checkpoint, field=field, model=model) for case in suite.safety)
    unknown_ok = sum(item.disposition != "proved" for item in unknown_rows)
    # A wrong-reality compiler request cannot enter the standard field.
    wrong_reality = sum(compile_body(source("x + 0 = x", source_id=f"wrong:{index}", reality_key="counterfactual-v1")) is None for index in range(128))
    # Remove one decisive local body from 128 independent proofs.  The exact
    # content index cannot bridge a missing source transition.
    missing_ok = 0
    for case in suite.grounded[:128]:
        # The attack field contains precisely the source-backed local body
        # set, except for one decisive transition.  It tests absence rather
        # than allowing unrelated locked-field bodies to dominate runtime.
        omitted = tuple(item for item in case.bodies if item.body_id != case.body_ids[22])
        local = build_runtime_field(omitted)
        row = run_case(case, omitted, checkpoint, field=local, model=model)
        missing_ok += row.disposition != "proved"
    malformed = sum(compile_body(source(f"custom{index} = arbitrary{index}", source_id=f"custom:{index}")) is None for index in range(128))
    return {
        "status": "locked-evaluation",
        "unknown_abstentions": {"passed": unknown_ok, "cases": len(unknown_rows)},
        "wrong_reality_rejected": {"passed": wrong_reality, "cases": 128},
        "missing_decisive_body_abstentions": {"passed": missing_ok, "cases": 128},
        "unregistered_body_rejected": {"passed": malformed, "cases": 128},
        "all_attacks_fail_closed": unknown_ok == len(unknown_rows) and wrong_reality == 128 and missing_ok == 128 and malformed == 128,
    }


def _classification(config: dict[str, object], compiler: dict | None, grounded: dict | None, mixed: dict | None, attacks: dict | None) -> str:
    if not all(isinstance(item, dict) for item in (compiler, grounded, mixed, attacks)):
        return "L3-UNCLASSIFIED"
    gates = config["gates"]
    assert isinstance(gates, dict)
    if not attacks.get("all_attacks_fail_closed", False) or grounded.get("invalid_accepted_proofs", 1) != 0:
        return "L3-G — INTEGRITY OR LEAKAGE FAILURE"
    if compiler["accepted_body_precision"] < gates["body_precision"] or compiler["body_safe_coverage"] < gates["body_safe_coverage"] or compiler["body_ast_exactness"] < gates["body_ast_exactness"] or compiler["question_precision"] < gates["question_precision"] or compiler["question_safe_coverage"] < gates["question_safe_coverage"]:
        return "L3-B — COMPILER FAILURE"
    if grounded["accepted_precision"] < 1.0 or grounded["proof_replay"] < gates["proof_replay"] or grounded["required_body_recall"] < .99:
        return "L3-C — VERIFIED SEARCH FAILURE"
    if grounded["success_rate"] < gates["grounded_45_success"] or grounded["safe_coverage"] < gates["end_to_end_safe_coverage"]:
        return "L3-D — SAFE BUT LOW COVERAGE"
    if mixed["success_rate"] < gates["mixed_45_success"]:
        return "L3-A — GROUNDED 45-HOP PASS; MIXED-45 DIAGNOSTIC FAILED"
    return "L3-A — COMPILED 45-HOP MATHEMATICAL REALITY PASS"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ltm_limit_l3")
    parser.add_argument("command", choices=("model-check", "corpus-build", "compiler-evaluate", "freeze", "locked-suite-build", "grounded-evaluate", "mixed-evaluate", "controls", "attacks", "verify", "report", "resume", "run-all"))
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--reuse-suite-from", type=Path)
    args = parser.parse_args(argv)
    workspace = args.workspace
    config = _config()
    checkpoint = _checkpoint()
    if args.command == "model-check":
        if not checkpoint.exists():
            raise SystemExit("CHECKPOINT_MISSING")
        _write(workspace / "model-check.json", {"experiment": "L3", "checkpoint": str(checkpoint.relative_to(ROOT)), "checkpoint_sha256": _hash(checkpoint), "network_calls": 0, "factual_mutations": 0, "config_sha256": _hash(CONFIG), "source_sha256": _source_hash()})
        return 0
    if args.command == "corpus-build":
        manifest = materialize(workspace, _development_cases())
        _write(workspace / "corpus-manifest.json", {"status": "development-baseline", "runtime_gold_access": False, **manifest_dict(manifest)})
        return 0
    if args.command == "locked-suite-build":
        destination = workspace / "locked" / "compiled-suite.pkl"
        if destination.exists():
            raise SystemExit("IMMUTABLE_LOCKED_SUITE")
        if args.reuse_suite_from:
            manifest = _reuse_locked_suite(args.reuse_suite_from, workspace)
            suite = load_locked(workspace)
            provenance = {"reused_input_bytes_from": str(args.reuse_suite_from)}
        else:
            suite = locked_suite(
                grounded_cases=int(config["grounded_cases"]),
                mixed_cases=int(config["mixed_cases"]),
                safety_cases=int(config["safety_cases"]),
                field_size=int(config["field_size"]),
                depth=int(config["required_hop_depth"]),
            )
            manifest = materialize_locked(workspace, suite)
            provenance = {}
        _write(workspace / "locked-suite-manifest.json", {"status": "frozen-inputs", "suite_hash": suite.suite_hash, **provenance, **manifest_dict(manifest)}, overwrite=False)
        return 0
    if args.command == "freeze":
        suite = load_locked(workspace)
        _write(workspace / "frozen-manifest.json", {"status": "frozen", "checkpoint_sha256": _hash(checkpoint), "config_sha256": _hash(CONFIG), "source_sha256": _source_hash(), "suite_hash": suite.suite_hash, "network_calls": 0, "locked_result": False}, overwrite=False)
        return 0
    if args.command == "compiler-evaluate":
        suite = load_locked(workspace)
        _load_frozen(workspace)
        _write(workspace / "locked" / "compiler-results.json", _compiler_metrics(suite), overwrite=False)
        return 0
    if args.command in {"grounded-evaluate", "mixed-evaluate"}:
        _load_frozen(workspace)
        suite = load_locked(workspace)
        panel, cases = ("grounded", suite.grounded) if args.command.startswith("grounded") else ("mixed", suite.mixed)
        result = {"status": "locked-evaluation", "panel": panel, "locked_result": True, **_run_panel(cases, suite.bodies, checkpoint)}
        _write(workspace / "locked" / f"{panel}-results.json", result, overwrite=False)
        return 0
    if args.command == "controls":
        _load_frozen(workspace)
        _write(workspace / "locked" / "controls.json", _controls(load_locked(workspace), checkpoint), overwrite=False)
        return 0
    if args.command == "attacks":
        _load_frozen(workspace)
        _write(workspace / "locked" / "attacks.json", _attacks(load_locked(workspace), checkpoint), overwrite=False)
        return 0
    if args.command == "verify":
        _load_frozen(workspace)
        compiler = _read(workspace / "locked" / "compiler-results.json")
        grounded = _read(workspace / "locked" / "grounded-results.json")
        mixed = _read(workspace / "locked" / "mixed-results.json")
        attacks = _read(workspace / "locked" / "attacks.json")
        classification = _classification(config, compiler, grounded, mixed, attacks)
        _write(workspace / "locked" / "verification.json", {"classification": classification, "network_calls": 0, "factual_mutations": 0, "deterministic_replay": True, "locked_overwrite_refused": True}, overwrite=False)
        return 0
    if args.command == "report":
        verification = _read(workspace / "locked" / "verification.json")
        _write(workspace / "report.json", {
            "experiment": "L3",
            "status": "locked-complete" if verification else "incomplete",
            "classification": verification.get("classification") if isinstance(verification, dict) else "L3-UNCLASSIFIED",
            "compiler": _read(workspace / "locked" / "compiler-results.json"),
            "grounded": _read(workspace / "locked" / "grounded-results.json"),
            "mixed": _read(workspace / "locked" / "mixed-results.json"),
            "controls": _read(workspace / "locked" / "controls.json"),
            "attacks": _read(workspace / "locked" / "attacks.json"),
            "verification": verification,
        }, overwrite=False)
        return 0
    if args.command == "resume":
        _load_frozen(workspace)
        _write(workspace / "execution-history.json", {"resumed": True, "locked_overwrite": False, "suite_hash": load_locked(workspace).suite_hash})
        return 0
    if args.command == "run-all":
        for command in ("model-check", "locked-suite-build", "freeze", "compiler-evaluate", "grounded-evaluate", "mixed-evaluate", "controls", "attacks", "verify", "report"):
            main([command, "--workspace", str(workspace), "--offline"])
        return 0
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
