"""CLI for the G2.4 controlled atom-vector experiment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .encoder import model_check
from .evaluate import develop, evaluate, freeze, locked_suite_build
from .report import write_report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m topology_g24")
    parser.add_argument("command", choices=("model-check", "dataset-build", "develop", "freeze", "locked-suite-build", "evaluate", "report", "verify", "run-all"))
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--limit", type=int, default=None, help="development-only smoke limit")
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "model-check":
        payload = model_check(); args.workspace.mkdir(parents=True, exist_ok=True); (args.workspace / "model-check.json").write_text(json.dumps(payload, indent=2) + "\n")
    elif args.command == "dataset-build":
        from .dataset import build_split
        build_split("train", args.workspace); build_split("development", args.workspace)
    elif args.command == "develop":
        develop(args.workspace, limit=args.limit)
    elif args.command == "freeze":
        freeze(args.workspace)
    elif args.command == "locked-suite-build":
        locked_suite_build(args.workspace)
    elif args.command == "evaluate":
        evaluate(args.workspace, limit=args.limit)
    elif args.command == "run-all":
        develop(args.workspace, limit=args.limit); freeze(args.workspace); locked_suite_build(args.workspace); evaluate(args.workspace, limit=args.limit)
    elif args.command == "report":
        write_report(args.workspace, Path("docs/experiments/gaps/g02-4/report.md"))
        print((args.workspace / "locked-results.json").read_text())
    elif args.command == "verify":
        print((args.workspace / "locked-results.json").read_text())
