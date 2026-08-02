from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .evaluate import develop, evaluate_locked, freeze
from .report import write_report


def main() -> None:
    parser = argparse.ArgumentParser(prog="micro_ltm3")
    parser.add_argument("command", choices=("develop", "freeze", "evaluate", "report", "run-all", "verify"))
    parser.add_argument("--workspace", type=Path, default=Path("workspaces/micro-ltm-3"))
    args = parser.parse_args()
    if args.command == "develop":
        print(json.dumps(develop(args.workspace), indent=2, sort_keys=True))
    elif args.command == "freeze":
        print(json.dumps(freeze(args.workspace), indent=2, sort_keys=True))
    elif args.command == "evaluate":
        print(json.dumps(evaluate_locked(args.workspace)["metrics"], indent=2, sort_keys=True))
    elif args.command == "report":
        print(write_report(args.workspace))
    elif args.command == "verify":
        manifest = args.workspace / "frozen-manifest.json"
        if not manifest.exists():
            raise FileNotFoundError("frozen manifest missing")
        values = json.loads(manifest.read_text())
        for key, filename in (("selected_sha256", "selected.json"), ("train_sha256", "train.jsonl"), ("dev_sha256", "dev.jsonl")):
            path = args.workspace / filename
            if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != values[key]:
                raise RuntimeError(f"frozen artifact hash mismatch: {filename}")
        if not (args.workspace / "locked-results.json").exists():
            raise FileNotFoundError("locked result missing")
        print(json.dumps({"verified": True, "manifest": values}, indent=2, sort_keys=True))
    else:
        develop(args.workspace)
        freeze(args.workspace)
        evaluate_locked(args.workspace)
        print(write_report(args.workspace))


if __name__ == "__main__":
    main()
