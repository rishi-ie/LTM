from __future__ import annotations

import argparse
import json
from pathlib import Path

from .encode import encode_split, model_check
from .evaluate import develop, evaluate_locked, freeze, locked_suite_build, verify
from .report import report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="topology_g21")
    parser.add_argument("command", choices=("model-check", "dataset-build", "embed", "develop", "freeze", "locked-suite-build", "evaluate", "report", "verify", "run-all"))
    parser.add_argument("--workspace", default="workspaces/topology-g2-1")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv); workspace = Path(args.workspace).resolve()
    if args.command == "model-check": result = model_check()
    elif args.command == "dataset-build":
        from .dataset import generate_cases, write_cases
        result = {}
        for split in ("train", "development"):
            cases = generate_cases(split); write_cases(cases, workspace / split / "inputs.jsonl", False); write_cases(cases, workspace / split / "gold.jsonl", True); result[split] = len(cases)
    elif args.command == "embed": result = {split: str(encode_split(split, workspace)) for split in ("train", "development", "locked")}
    elif args.command == "develop": result = develop(workspace)
    elif args.command == "freeze": result = freeze(workspace)
    elif args.command == "locked-suite-build": result = locked_suite_build(workspace)
    elif args.command == "evaluate": result = evaluate_locked(workspace)
    elif args.command == "report": result = report(workspace)
    elif args.command == "verify": result = verify(workspace)
    else:
        model_check(); develop(workspace); freeze(workspace); locked_suite_build(workspace); evaluate_locked(workspace); result = report(workspace)
    print(json.dumps(result, indent=2, sort_keys=True)); return 0
