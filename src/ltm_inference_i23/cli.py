"""CLI for I2.3's separate runtime and evaluator lifecycle."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from . import lifecycle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("model-check", "dataset-build", "develop", "development-controls", "development-gate", "freeze", "runtime-infer", "evaluator-score", "verify", "run-all"))
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    commands = {
        "model-check": lifecycle.model_check,
        "dataset-build": lifecycle.dataset_build,
        "develop": lifecycle.develop,
        "development-controls": lifecycle.development_controls,
        "development-gate": lifecycle.development_gate,
        "freeze": lifecycle.freeze,
        "runtime-infer": lifecycle.runtime_infer,
        "evaluator-score": lifecycle.evaluator_score,
        "verify": lifecycle.verify,
    }
    if args.command != "run-all":
        commands[args.command](args.workspace)
        return 0
    lifecycle.model_check(args.workspace)
    lifecycle.dataset_build(args.workspace)
    lifecycle.develop(args.workspace)
    lifecycle.development_controls(args.workspace)
    lifecycle.freeze(args.workspace)
    for command in ("runtime-infer", "evaluator-score"):
        subprocess.run([sys.executable, "-m", "ltm_inference_i23", command, "--workspace", str(args.workspace), "--offline"], check=True)
    lifecycle.verify(args.workspace)
    return 0
