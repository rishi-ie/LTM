"""I3 command line lifecycle."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import lifecycle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("model-check", "axiom-bank-build", "dataset-build", "develop", "calibrate", "development-controls", "development-gate", "freeze", "locked-suite-build", "evaluate", "stress-evaluate", "reality-evaluate", "intervene", "llm-export", "verify", "report", "resume", "run-all"))
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    commands = {
        "model-check": lifecycle.model_check,
        "axiom-bank-build": lifecycle.axiom_bank_build,
        "dataset-build": lifecycle.dataset_build,
        "develop": lifecycle.develop,
        "calibrate": lifecycle.calibrate,
        "development-controls": lifecycle.development_controls,
        "development-gate": lifecycle.development_gate,
        "freeze": lifecycle.freeze,
        "evaluate": lifecycle.evaluate,
        "stress-evaluate": lifecycle.stress_evaluate,
        "reality-evaluate": lifecycle.reality_evaluate,
        "intervene": lifecycle.intervene,
        "llm-export": lifecycle.llm_export,
        "verify": lifecycle.verify,
    }
    if args.command == "locked-suite-build":
        return 0
    if args.command == "report":
        from .report import write_report

        write_report(args.workspace)
        return 0
    if args.command == "resume":
        if not (args.workspace / "dataset-manifest.json").exists():
            lifecycle.dataset_build(args.workspace)
        if not (args.workspace / "development-results.json").exists():
            lifecycle.develop(args.workspace)
        return 0
    if args.command != "run-all":
        commands[args.command](args.workspace)
        return 0
    lifecycle.model_check(args.workspace)
    lifecycle.axiom_bank_build(args.workspace)
    lifecycle.dataset_build(args.workspace)
    lifecycle.develop(args.workspace)
    lifecycle.calibrate(args.workspace)
    lifecycle.development_controls(args.workspace)
    lifecycle.freeze(args.workspace)
    lifecycle.evaluate(args.workspace)
    lifecycle.stress_evaluate(args.workspace)
    lifecycle.reality_evaluate(args.workspace)
    lifecycle.intervene(args.workspace)
    lifecycle.llm_export(args.workspace)
    lifecycle.verify(args.workspace)
    from .report import write_report

    write_report(args.workspace)
    return 0
