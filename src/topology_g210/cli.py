"""Command line lifecycle for G2.10."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import evaluate

COMMANDS = (
    "model-check", "representation-check", "dataset-build", "kernel-develop", "kernel-freeze",
    "kernel-locked-suite-build", "kernel-evaluate", "develop", "freeze", "locked-suite-build",
    "evaluate", "verify", "report", "resume", "run-all",
)


def _report(workspace: Path) -> dict[str, object]:
    from .report import write_report

    return write_report(workspace)


def _run_all(workspace: Path) -> dict[str, object]:
    if not (workspace / "model-check.json").exists(): evaluate.model_check(workspace)
    if not (workspace / "representation-check.json").exists(): evaluate.representation_check(workspace)
    if not (workspace / "dataset-manifest.json").exists(): evaluate.dataset_build(workspace)
    development = evaluate.kernel_develop(workspace) if not (workspace / "kernel-development-results.json").exists() else json.loads((workspace / "kernel-development-results.json").read_text())
    if not development["kernel_passed"]: return _report(workspace)
    if not (workspace / "kernel-frozen-manifest.json").exists(): evaluate.kernel_freeze(workspace)
    if not (workspace / "kernel_locked" / "inputs.jsonl").exists(): evaluate.kernel_locked_suite_build(workspace)
    kernel = evaluate.kernel_evaluate(workspace) if not (workspace / "kernel-results.json").exists() else json.loads((workspace / "kernel-results.json").read_text())
    if not kernel["kernel_passed"]: return _report(workspace)
    full = evaluate.develop(workspace) if not (workspace / "development-results.json").exists() else json.loads((workspace / "development-results.json").read_text())
    if not full["full_passed"]: return _report(workspace)
    if not (workspace / "frozen-manifest.json").exists(): evaluate.freeze(workspace)
    if not (workspace / "locked" / "inputs.jsonl").exists(): evaluate.locked_suite_build(workspace)
    if not (workspace / "locked-results.json").exists(): evaluate.evaluate_locked(workspace)
    evaluate.verify(workspace)
    return _report(workspace)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m topology_g210")
    parser.add_argument("command", choices=COMMANDS)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv); workspace = args.workspace.resolve()
    actions = {
        "model-check": evaluate.model_check, "representation-check": evaluate.representation_check,
        "dataset-build": evaluate.dataset_build, "kernel-develop": evaluate.kernel_develop,
        "kernel-freeze": evaluate.kernel_freeze, "kernel-locked-suite-build": evaluate.kernel_locked_suite_build,
        "kernel-evaluate": evaluate.kernel_evaluate, "develop": evaluate.develop, "freeze": evaluate.freeze,
        "locked-suite-build": evaluate.locked_suite_build, "evaluate": evaluate.evaluate_locked,
        "verify": evaluate.verify, "report": _report, "resume": _run_all, "run-all": _run_all,
    }
    print(json.dumps(actions[args.command](workspace), indent=2, sort_keys=True, default=str))
    return 0
