from __future__ import annotations

import argparse
from pathlib import Path

from .audit import assert_clean, write_architecture_manifest, write_audit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ltm")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("audit", "verify"):
        command = sub.add_parser(name)
        command.add_argument("--workspace", type=Path, required=True)
        command.add_argument("--offline", action="store_true")
    sub.add_parser("lock")
    args = parser.parse_args(argv)
    if args.command == "lock":
        write_architecture_manifest(Path.cwd())
        return 0
    result = write_audit(Path.cwd(), args.workspace)
    assert_clean(result)
    return 0
