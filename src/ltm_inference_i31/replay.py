"""Process-isolated formal proof replay used by the prompt audit."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .dataset import body_from_obj, expr_from_obj
from .formal import verify_proof
from .schemas import FormalProofStep


def main() -> int:
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    source = expr_from_obj(payload["source"])
    goal = expr_from_obj(payload["goal"])
    bodies = {item["body_id"]: body_from_obj(item) for item in payload["bodies"]}
    proof = tuple(FormalProofStep(item["body_id"], tuple(item["path"]), bool(item["reverse"]), expr_from_obj(item["before"]), expr_from_obj(item["after"])) for item in payload["proof"])
    print(json.dumps({"valid": verify_proof(source, goal, proof, bodies, payload["reality_key"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
