from __future__ import annotations

import argparse
import json
from pathlib import Path

from .encoder import model_check
from .evaluate import (
    audit_development,
    dataset_build,
    develop,
    evaluate_locked,
    freeze,
    locked_suite_build,
    verify,
    write_json,
)
from .report import report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="topology_g23")
    parser.add_argument("command", choices=("model-check", "dataset-build", "diagnose", "develop", "freeze", "locked-suite-build", "evaluate", "report", "verify", "run-all"))
    parser.add_argument("--workspace", default="workspaces/topology-g2-3-r4")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv); workspace = Path(args.workspace).resolve()
    if args.command == "model-check": result = model_check(); write_json(workspace / "model-check.json", result)
    elif args.command == "dataset-build": result = dataset_build(workspace)
    elif args.command == "diagnose": result = audit_development(workspace)
    elif args.command == "develop": result = develop(workspace)
    elif args.command == "freeze": result = freeze(workspace)
    elif args.command == "locked-suite-build": result = locked_suite_build(workspace)
    elif args.command == "evaluate": result = evaluate_locked(workspace)
    elif args.command == "report": result = report(workspace)
    elif args.command == "verify": result = verify(workspace)
    else:
        result = model_check(); write_json(workspace / "model-check.json", result)
        develop(workspace); freeze(workspace); locked_suite_build(workspace); evaluate_locked(workspace); verify(workspace); result = report(workspace)
    print(json.dumps(result, indent=2, sort_keys=True, default=str)); return 0
