"""Command line boundary for the isolated G2.9 experiment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import evaluate
from .report import write_report

COMMANDS = ("model-check", "dataset-build", "atom-bank-build", "kernel-develop", "kernel-freeze", "kernel-locked-suite-build", "kernel-evaluate", "develop", "freeze", "locked-suite-build", "evaluate", "migrate", "integrate", "verify", "report", "resume", "run-all")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m topology_g29")
    parser.add_argument("command", choices=COMMANDS)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    functions = {
        "model-check": evaluate.model_check, "dataset-build": evaluate.dataset_build,
        "atom-bank-build": evaluate.atom_bank_build, "kernel-develop": evaluate.kernel_develop,
        "kernel-freeze": evaluate.kernel_freeze, "kernel-locked-suite-build": evaluate.kernel_locked_suite_build,
        "kernel-evaluate": evaluate.kernel_evaluate, "develop": evaluate.develop, "freeze": evaluate.freeze,
        "locked-suite-build": evaluate.locked_suite_build, "evaluate": evaluate.evaluate_locked,
        "migrate": evaluate.migrate, "integrate": evaluate.integrate, "verify": evaluate.verify,
        "resume": evaluate.run_all, "run-all": evaluate.run_all,
    }
    if args.command == "report":
        write_report(args.workspace, Path("docs/experiments/gaps/g02-9/report.md"))
        result: object = {"report": "docs/experiments/gaps/g02-9/report.md"}
    else:
        result = functions[args.command](args.workspace)
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
