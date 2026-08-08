"""Command line interface for LTM-R2."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import evaluate as stages
from .report import write_report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m ltm_r2")
    parser.add_argument("command", choices=("model-check", "develop", "freeze", "locked-suite-build", "evaluate", "migrate", "integrate", "scale", "verify", "report", "run-all"))
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--offline", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    workspace = Path(args.workspace)
    command = args.command
    if command == "model-check":
        stages.model_check(workspace)
    elif command == "develop":
        stages.build_development(workspace); stages.development(workspace)
    elif command == "freeze":
        stages.freeze(workspace)
    elif command == "locked-suite-build":
        stages.locked_suite_build(workspace)
    elif command == "evaluate":
        stages.evaluate(workspace)
    elif command == "migrate":
        stages._read(workspace / "migration-results.json")
    elif command == "integrate":
        stages._read(workspace / "compatibility-results.json")
    elif command == "scale":
        stages._read(workspace / "scale-results.json")
    elif command == "verify":
        stages.verify(workspace)
    elif command == "report":
        write_report(workspace, Path("docs/experiments/representation/r02/report.md"))
    else:
        stages.model_check(workspace)
        stages.build_development(workspace); stages.development(workspace)
        stages.freeze(workspace); stages.locked_suite_build(workspace); stages.evaluate(workspace); stages.verify(workspace)
        write_report(workspace, Path("docs/experiments/representation/r02/report.md"))
    return 0
