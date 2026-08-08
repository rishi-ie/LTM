"""CLI for the interrupt-safe G2.6 stages."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .dataset import build_split
from .encoder import model_check
from .evaluate import (
    develop,
    freeze,
    kernel_evaluate,
    kernel_locked_suite_build,
    locked_suite_build,
    run_all,
    verify,
)

COMMANDS = ("model-check", "dataset-build", "kernel-develop", "kernel-freeze", "kernel-locked-suite-build", "kernel-evaluate", "develop", "freeze", "locked-suite-build", "evaluate", "report", "verify", "resume", "run-all")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m topology_g26")
    parser.add_argument("command", choices=COMMANDS)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    workspace = args.workspace
    if args.command == "model-check":
        workspace.mkdir(parents=True, exist_ok=True)
        (workspace / "model-check.json").write_text(json.dumps(model_check(), indent=2) + "\n", encoding="utf-8")
    elif args.command == "dataset-build":
        print(json.dumps({split: build_split(split, workspace) for split in ("train", "development")}, indent=2, sort_keys=True))
    elif args.command in {"kernel-develop", "develop"}:
        print(json.dumps(develop(workspace, limit=args.limit), indent=2, sort_keys=True))
    elif args.command in {"kernel-freeze", "freeze"}:
        print(json.dumps(freeze(workspace), indent=2, sort_keys=True))
    elif args.command == "kernel-locked-suite-build":
        print(json.dumps(kernel_locked_suite_build(workspace), indent=2, sort_keys=True))
    elif args.command == "locked-suite-build":
        print(json.dumps(locked_suite_build(workspace), indent=2, sort_keys=True))
    elif args.command in {"kernel-evaluate", "evaluate"}:
        print(json.dumps(kernel_evaluate(workspace), indent=2, sort_keys=True))
    elif args.command in {"resume", "run-all"}:
        print(json.dumps(run_all(workspace, limit=args.limit), indent=2, sort_keys=True))
    elif args.command == "verify":
        print(json.dumps(verify(workspace), indent=2, sort_keys=True))
    elif args.command == "report":
        from .report import write_report
        write_report(workspace, Path("docs/experiments/gaps/g02-6/report.md"))
    else:
        raise RuntimeError("unsupported G2.6 stage")
