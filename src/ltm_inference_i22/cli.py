"""CLI for I2.2."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import evaluate
from .report import write_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("model-check", "dataset-build", "develop", "freeze", "evaluate", "controls", "intervene", "verify", "report", "run-all"))
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    if args.command == "model-check": evaluate.model_check(args.workspace)
    elif args.command == "dataset-build": evaluate.dataset_build(args.workspace)
    elif args.command == "develop": evaluate.develop(args.workspace)
    elif args.command == "freeze": evaluate.freeze(args.workspace)
    elif args.command == "evaluate": evaluate.evaluate(args.workspace)
    elif args.command == "controls": evaluate.controls(args.workspace)
    elif args.command == "intervene": evaluate.intervene(args.workspace)
    elif args.command == "verify": evaluate.verify(args.workspace)
    elif args.command == "report": write_report(args.workspace, Path(__file__).resolve().parents[2] / "docs/experiments/inference/i02-2/report.md")
    else:
        evaluate.model_check(args.workspace); evaluate.dataset_build(args.workspace); evaluate.develop(args.workspace); evaluate.freeze(args.workspace); evaluate.evaluate(args.workspace); evaluate.controls(args.workspace); evaluate.intervene(args.workspace); evaluate.verify(args.workspace)
    return 0
