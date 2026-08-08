from __future__ import annotations

import argparse
import json
from pathlib import Path

from .audit import audit, build, verify
from .report import report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LTM-R1 vector-native representation audit")
    parser.add_argument("command", choices=("build", "audit", "verify", "report", "run-all"))
    parser.add_argument("--workspace", default="workspaces/topology-field-r1")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)
    workspace = Path(args.workspace).resolve()
    if args.command == "build": result = build(workspace)
    elif args.command == "audit": result = audit(workspace)
    elif args.command == "verify": result = verify(workspace)
    elif args.command == "report": result = report(workspace)
    else:
        if not (workspace / "build.json").exists(): build(workspace)
        if not (workspace / "audit-results.json").exists(): audit(workspace)
        result = report(workspace)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0
