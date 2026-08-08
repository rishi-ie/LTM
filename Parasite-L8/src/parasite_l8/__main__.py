from __future__ import annotations

import argparse
import json
from pathlib import Path

from .runtime import L8Runtime


def main() -> int:
    parser = argparse.ArgumentParser(prog="parasite_l8")
    parser.add_argument("command", choices=("model-check", "policy-compile", "run-all"))
    parser.add_argument("--workspace", default="Parasite-L8/var/l8-r1")
    args = parser.parse_args()
    workspace = Path(args.workspace)
    if args.command == "model-check":
        runtime = L8Runtime.open(workspace)
        print(json.dumps({"baseline": runtime.baseline_manifest, "trainable_parameters": 0}, sort_keys=True))
        return 0
    if args.command == "policy-compile":
        runtime = L8Runtime.open(workspace)
        policy = runtime.compile_policy("default", [])
        print(json.dumps({"policy_id": policy.policy_id, "hash": policy.hash}, sort_keys=True))
        return 0
    import importlib.util
    runner_path = Path(__file__).resolve().parents[2] / "benchmarks/run_l8.py"
    spec = importlib.util.spec_from_file_location("parasite_l8_acceptance_runner", runner_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("RUNNER_MISSING")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    return runner.run(workspace)


if __name__ == "__main__":
    raise SystemExit(main())
