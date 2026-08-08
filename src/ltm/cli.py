from __future__ import annotations

import argparse
from pathlib import Path

from .audit import assert_clean, write_architecture_manifest, write_audit
from .local_archive import execute as archive_execute
from .local_archive import plan as archive_plan
from .local_archive import restore as archive_restore
from .local_archive import verify as archive_verify


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ltm")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("audit", "verify"):
        command = sub.add_parser(name)
        command.add_argument("--workspace", type=Path, required=True)
        command.add_argument("--offline", action="store_true")
    sub.add_parser("lock")
    command = sub.add_parser("archive-plan")
    command.add_argument("--destination", type=Path, required=True)
    command.add_argument("--min-workspace-mib", type=int, default=100)
    command = sub.add_parser("archive-execute")
    command.add_argument("--plan", type=Path, required=True)
    command = sub.add_parser("archive-verify")
    command.add_argument("--archive", type=Path, required=True)
    command = sub.add_parser("archive-restore")
    command.add_argument("--archive", type=Path, required=True)
    command.add_argument("--item", required=True)
    args = parser.parse_args(argv)
    if args.command == "lock":
        write_architecture_manifest(Path.cwd())
        return 0
    if args.command == "archive-plan":
        target = archive_plan(Path.cwd(), args.destination, args.min_workspace_mib)
        print(target)
        return 0
    if args.command == "archive-execute":
        print(archive_execute(Path.cwd(), args.plan))
        return 0
    if args.command == "archive-verify":
        print(archive_verify(Path.cwd(), args.archive))
        return 0
    if args.command == "archive-restore":
        print(archive_restore(Path.cwd(), args.archive, args.item))
        return 0
    result = write_audit(Path.cwd(), args.workspace)
    assert_clean(result)
    return 0
