from __future__ import annotations

import argparse
from pathlib import Path

from .evaluate import build_inputs, develop, evaluate_locked, freeze, model_check, replay, run_all
from .report import write_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ltm_i1")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("model-check", "develop", "freeze", "locked-suite-build", "evaluate", "verify", "report", "run-all"):
        command = sub.add_parser(name)
        command.add_argument("--workspace", type=Path, required=True)
        command.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)
    workspace = args.workspace
    if args.command == "model-check": model_check(workspace)
    elif args.command == "develop": develop(workspace)
    elif args.command == "freeze": freeze(workspace)
    elif args.command == "locked-suite-build": build_inputs(workspace)
    elif args.command == "evaluate": evaluate_locked(workspace)
    elif args.command == "verify": replay(workspace)
    elif args.command == "report": write_report(workspace, Path("docs/experiments/integration/i01/report.md"))
    elif args.command == "run-all": run_all(workspace)
    return 0

