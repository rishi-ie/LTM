"""CLI for staged G2.7 execution."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .encoder import model_check
from .evaluate import (
    atom_bank_build,
    dataset_build,
    evaluate_locked,
    freeze,
    kernel_develop,
    kernel_evaluate,
    kernel_freeze,
    kernel_locked_suite_build,
    locked_suite_build,
    run_all,
    verify,
)

COMMANDS = ("model-check", "dataset-build", "atom-bank-build", "kernel-develop", "kernel-freeze", "kernel-locked-suite-build", "kernel-evaluate", "develop", "freeze", "locked-suite-build", "evaluate", "report", "verify", "resume", "run-all")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m topology_g27")
    parser.add_argument("command", choices=COMMANDS)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    workspace = args.workspace
    if args.command == "model-check":
        workspace.mkdir(parents=True, exist_ok=True)
        output = model_check()
        (workspace / "model-check.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(output, indent=2, sort_keys=True))
    elif args.command == "dataset-build":
        print(json.dumps(dataset_build(workspace), indent=2, sort_keys=True))
    elif args.command == "atom-bank-build":
        print(json.dumps(atom_bank_build(workspace), indent=2, sort_keys=True))
    elif args.command in {"kernel-develop", "develop"}:
        print(json.dumps(kernel_develop(workspace), indent=2, sort_keys=True))
    elif args.command == "kernel-freeze":
        print(json.dumps(kernel_freeze(workspace), indent=2, sort_keys=True))
    elif args.command == "kernel-locked-suite-build":
        print(json.dumps(kernel_locked_suite_build(workspace), indent=2, sort_keys=True))
    elif args.command == "kernel-evaluate":
        print(json.dumps(kernel_evaluate(workspace), indent=2, sort_keys=True))
    elif args.command == "freeze":
        print(json.dumps(freeze(workspace), indent=2, sort_keys=True))
    elif args.command == "locked-suite-build":
        print(json.dumps(locked_suite_build(workspace), indent=2, sort_keys=True))
    elif args.command == "evaluate":
        print(json.dumps(evaluate_locked(workspace), indent=2, sort_keys=True))
    elif args.command in {"resume", "run-all"}:
        print(json.dumps(run_all(workspace), indent=2, sort_keys=True))
    elif args.command == "verify":
        print(json.dumps(verify(workspace), indent=2, sort_keys=True))
    elif args.command == "report":
        from .report import write_report
        write_report(workspace, Path("docs/experiments/gaps/g02-7/report.md"))
    else:
        raise RuntimeError("unsupported G2.7 command")
