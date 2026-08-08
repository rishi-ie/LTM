"""Command line interface for G2.8."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import evaluate
from .report import write_report

COMMANDS = (
    "model-check", "dataset-build", "atom-bank-build", "kernel-develop", "kernel-freeze",
    "kernel-locked-suite-build", "kernel-evaluate", "develop", "freeze", "locked-suite-build",
    "evaluate", "migrate", "integrate", "verify", "report", "resume", "run-all",
)


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m topology_g28")
    parser.add_argument("command", choices=COMMANDS)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    command = args.command
    workspace = args.workspace
    if command == "model-check": result = evaluate.model_check(workspace)
    elif command == "dataset-build": result = evaluate.dataset_build(workspace)
    elif command == "atom-bank-build": result = evaluate.atom_bank_build(workspace)
    elif command == "kernel-develop": result = evaluate.kernel_develop(workspace)
    elif command == "kernel-freeze": result = evaluate.kernel_freeze(workspace)
    elif command == "kernel-locked-suite-build": result = evaluate.kernel_locked_suite_build(workspace)
    elif command == "kernel-evaluate": result = evaluate.kernel_evaluate(workspace)
    elif command == "develop": result = evaluate.develop(workspace)
    elif command == "freeze": result = evaluate.freeze(workspace)
    elif command == "locked-suite-build": result = evaluate.locked_suite_build(workspace)
    elif command == "evaluate": result = evaluate.evaluate_locked(workspace)
    elif command == "migrate": result = evaluate.migrate(workspace)
    elif command == "integrate": result = evaluate.integrate(workspace)
    elif command == "verify": result = evaluate.verify(workspace)
    elif command == "report":
        write_report(workspace, Path("docs/experiments/gaps/g02-8/report.md"))
        result = {"report": "docs/experiments/gaps/g02-8/report.md"}
    elif command in {"resume", "run-all"}: result = evaluate.run_all(workspace)
    else: raise RuntimeError("unsupported command")
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
