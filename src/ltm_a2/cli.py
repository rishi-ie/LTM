"""Command line entry point for the read-only LTM-A2 audit."""

from __future__ import annotations

import argparse
from pathlib import Path

from .audit import run_audit
from .report import write_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ltm_a2")
    parser.add_argument("command", choices=("audit", "report", "run-all"))
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    if args.command in ("audit", "run-all"):
        run_audit(root, args.workspace)
    if args.command in ("report", "run-all"):
        write_report(args.workspace, root / "docs/audits/2026-08-06-ltm-architecture-viability-audit.md")
    return 0
