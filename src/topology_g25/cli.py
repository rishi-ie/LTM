"""Command interface for the interrupt-safe G2.5 kernel stages."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .dataset import build_kernel_split
from .encoder import model_check
from .evaluate import (
    _atomic_json,
    kernel_develop,
    kernel_evaluate,
    kernel_freeze,
    kernel_locked_suite_build,
    run_kernel_all,
    verify_kernel,
)
from .report import write_report

COMMANDS = (
    "model-check",
    "dataset-build",
    "kernel-develop",
    "kernel-freeze",
    "kernel-locked-suite-build",
    "kernel-evaluate",
    "develop",
    "freeze",
    "locked-suite-build",
    "evaluate",
    "report",
    "verify",
    "resume",
    "run-all",
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m topology_g25")
    parser.add_argument("command", choices=COMMANDS)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument(
        "--limit", type=int, default=None, help="development-only smoke limit; it cannot be frozen"
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    workspace: Path = args.workspace
    if args.command == "model-check":
        workspace.mkdir(parents=True, exist_ok=True)
        _atomic_json(workspace / "model-check.json", model_check())
        return
    if args.command == "dataset-build":
        build_kernel_split("train", workspace)
        build_kernel_split("development", workspace)
        return
    if args.command == "kernel-develop":
        print(json.dumps(kernel_develop(workspace, limit=args.limit), indent=2, sort_keys=True))
        return
    if args.command == "kernel-freeze":
        print(json.dumps(kernel_freeze(workspace), indent=2, sort_keys=True))
        return
    if args.command == "kernel-locked-suite-build":
        print(json.dumps(kernel_locked_suite_build(workspace), indent=2, sort_keys=True))
        return
    if args.command == "kernel-evaluate":
        print(json.dumps(kernel_evaluate(workspace), indent=2, sort_keys=True))
        return
    if args.command in {"resume", "run-all"}:
        print(json.dumps(run_kernel_all(workspace), indent=2, sort_keys=True))
        return
    if args.command == "report":
        write_report(workspace, Path("docs/experiments/gaps/g02-5/report.md"))
        return
    if args.command == "verify":
        print(json.dumps(verify_kernel(workspace), indent=2, sort_keys=True))
        return
    # The full compiler is deliberately gated on the locked representation
    # decision.  These aliases make that boundary explicit rather than hiding
    # future Phase-B--D work behind a successful kernel command.
    raise RuntimeError(
        f"{args.command} is unavailable until the locked representation kernel passes"
    )
