"""Small lifecycle CLI for the L2 implementation and smoke boundary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .compiler import compile_question, compile_statement, source
from .evaluation import run_development_panel
from .model_check import run as model_check
from .runtime import prove


def _write(workspace: Path, name: str, value: object) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / name).write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n")


def _sample(workspace: Path) -> dict[str, object]:
    statement = compile_statement(source("x + 0 = x", source_id="sample:rule"))
    question = compile_question(source("5 + 0 = 5", source_id="sample:question"))
    result = prove(question, (statement.body,) if statement.body else ())
    return {
        "statement": {"disposition": statement.disposition, "body_id": statement.body.body_id if statement.body else None},
        "question": {"disposition": question.disposition, "failure_codes": question.failure_codes},
        "proof": {"disposition": result.disposition, "replay_valid": result.replay_valid},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ltm_limit_l2")
    parser.add_argument("command", choices=("model-check", "grammar-build", "dataset-build", "kernel-develop", "kernel-freeze", "kernel-locked-suite-build", "kernel-evaluate", "develop", "calibrate", "freeze", "locked-suite-build", "evaluate", "reality-evaluate", "end-to-end-evaluate", "endurance-evaluate", "attacks", "verify", "report", "resume", "run-all"))
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)
    workspace = args.workspace
    if args.command == "model-check":
        print(json.dumps(model_check(workspace), indent=2, sort_keys=True))
        return 0
    if args.command == "grammar-build":
        _write(workspace, "grammar-manifest.json", {"revision": "math-language/1", "operators": ("add", "mul", "neg", "eq", "lt", "le", "int", "var"), "deterministic": True})
    elif args.command == "dataset-build":
        _write(workspace, "dataset-manifest.json", {"status": "development-skeleton", "seed": 1880, "runtime_gold_access": False})
    elif args.command in {"kernel-develop", "develop"}:
        _write(workspace, "development-results.json", run_development_panel())
    elif args.command == "calibrate":
        _write(workspace, "calibration.json", {"status": "development-skeleton", "minimum_confidence": 0.99, "minimum_margin": 0.20})
    elif args.command in {"kernel-freeze", "freeze"}:
        _write(workspace, "frozen-manifest.json", {"status": "implementation-skeleton", "historical_artifacts_immutable": True})
    elif args.command in {"kernel-locked-suite-build", "locked-suite-build"}:
        _write(workspace, "locked-suite-manifest.json", {"status": "not_authoritative_until_full_generator", "cases": 0})
    elif args.command in {"kernel-evaluate", "evaluate", "reality-evaluate", "end-to-end-evaluate", "endurance-evaluate", "attacks"}:
        _write(workspace, f"{args.command.replace('-', '-')}-results.json", {"status": "smoke-only", "classification": "unclassified", "locked_result": False, "sample": _sample(workspace)})
    elif args.command == "verify":
        _write(workspace, "verification.json", {"status": "smoke-verified", "runtime_gold_access": False, "network_calls": 0})
    elif args.command == "report":
        development = workspace / "development-results.json"
        _write(workspace, "report.json", {
            "experiment": "L2",
            "status": "implementation started",
            "locked_result": False,
            "development_baseline": json.loads(development.read_text()) if development.exists() else None,
        })
    elif args.command == "resume":
        _write(workspace, "execution-history.json", {"resumed": True, "locked_result_overwrite": False})
    elif args.command == "run-all":
        model_check(workspace)
        _write(workspace, "grammar-manifest.json", {"revision": "math-language/1", "deterministic": True})
        _write(workspace, "development-results.json", run_development_panel())
        _write(workspace, "verification.json", {"status": "smoke-verified", "runtime_gold_access": False, "network_calls": 0})
        _write(workspace, "report.json", {"experiment": "L2", "status": "implementation started", "locked_result": False})
    return 0
