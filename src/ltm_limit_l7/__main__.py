from __future__ import annotations

import argparse
from pathlib import Path

from .dataset import build_cases, build_reality, manifest
from .experiment import controls, interventions, run_all


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m ltm_limit_l7")
    parser.add_argument("command", choices=("model-check", "reality-build", "suite-build", "freeze", "evaluate", "controls", "intervene", "verify", "report", "run-all"))
    parser.add_argument("--workspace", type=Path, default=Path("workspaces/ltm-limit-l7-r1"))
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    if args.command == "run-all":
        run_all(args.workspace)
        return
    field = build_reality()
    cases = build_cases(field)
    if args.command == "model-check":
        print({"trainable_parameters": 0, "model_bytes": 0, "learned_geometry": False})
    elif args.command in {"reality-build", "suite-build", "freeze"}:
        print(manifest(field, cases))
    elif args.command == "controls":
        print(controls(field, cases))
    elif args.command == "intervene":
        print(interventions(field, cases))
    else:
        # evaluate/verify/report are intentionally one immutable lifecycle.
        run_all(args.workspace)


if __name__ == "__main__":
    main()
