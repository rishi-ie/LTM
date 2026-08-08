"""CLI for I2.1."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import evaluate
from .report import write_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("model-check", "dataset-build", "minimap-build", "develop", "calibrate", "freeze", "locked-suite-build", "evaluate", "controls", "intervene", "verify", "report", "run-all"))
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    command = args.command
    if command == "model-check": evaluate.model_check(args.workspace)
    elif command == "dataset-build": evaluate.dataset_build(args.workspace)
    elif command == "minimap-build": evaluate.minimap_build(args.workspace)
    elif command == "develop": evaluate.develop(args.workspace)
    elif command == "calibrate": evaluate.calibrate(args.workspace)
    elif command == "freeze": evaluate.freeze(args.workspace)
    elif command == "locked-suite-build": evaluate.locked_suite_build(args.workspace)
    elif command == "evaluate": evaluate.evaluate(args.workspace)
    elif command == "controls": evaluate.controls(args.workspace)
    elif command == "intervene": evaluate.intervene(args.workspace)
    elif command == "verify": evaluate.verify(args.workspace)
    elif command == "report": write_report(args.workspace, Path(__file__).resolve().parents[2] / "docs/experiments/inference/i02-1/report.md")
    else: evaluate.run_all(args.workspace)
    return 0
