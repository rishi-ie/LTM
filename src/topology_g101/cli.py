from __future__ import annotations

import argparse
from pathlib import Path

from .runner import run, write_result


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m topology_g101")
    parser.add_argument("--model-path", type=Path, default=Path(".models/flan-t5-small"))
    parser.add_argument("--cases", type=int, default=256)
    parser.add_argument("--seed", type=int, default=20260826)
    parser.add_argument("--output", type=Path, default=Path("workspaces/topology-g10-1/locked-results.json"))
    args = parser.parse_args()
    result = run(args.model_path, seed=args.seed, cases=args.cases)
    write_result(args.output, result)
    print(result["classification"])
    print(result["metrics"])


if __name__ == "__main__":
    main()
