"""CLI for I1's fail-fast, immutable lifecycle."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import evaluate
from .report import write_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ltm_inference_i1")
    parser.add_argument("command", choices=("model-check", "dataset-build", "develop", "calibrate", "freeze", "locked-suite-build", "evaluate", "intervene", "naturalistic-evaluate", "verify", "report", "resume", "run-all"))
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "model-check": evaluate.model_check(args.workspace)
    elif args.command == "dataset-build": evaluate.dataset_build(args.workspace)
    elif args.command == "develop": evaluate.develop(args.workspace)
    elif args.command == "calibrate": evaluate.calibrate(args.workspace)
    elif args.command == "freeze": evaluate.freeze(args.workspace)
    elif args.command == "locked-suite-build": evaluate.locked_suite_build(args.workspace)
    elif args.command == "evaluate": evaluate.evaluate(args.workspace)
    elif args.command == "intervene": evaluate.interventions(args.workspace)
    elif args.command == "naturalistic-evaluate": evaluate.naturalistic(args.workspace)
    elif args.command == "verify": evaluate.verify(args.workspace)
    elif args.command == "report": write_report(args.workspace, Path("docs/experiments/inference/i01/report.md"))
    elif args.command == "resume": evaluate.run_all(args.workspace)
    else:
        evaluate.run_all(args.workspace)
        write_report(args.workspace, Path("docs/experiments/inference/i01/report.md"))
    return 0
