"""Process-separated L8 scorer; it never imports the runtime optimizer."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
L8_ROOT = ROOT / "Parasite-L8"
sys.path[:0] = [str(L8_ROOT / "src"), str(ROOT / "Parasite" / "src"), str(ROOT / "src")]

from parasite.field.store import FieldStore

from parasite_l8.contracts import CompiledPolicy, PolicyInstruction
from parasite_l8.evaluator import expected_outcome


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()
    workspace = Path(args.workspace)
    public = [json.loads(row) for row in (workspace / "public-cases.jsonl").read_text().splitlines()]
    gold = [json.loads(row) for row in (workspace / "evaluator-gold.jsonl").read_text().splitlines()]
    predictions = [json.loads(row) for row in (workspace / "predictions.jsonl").read_text().splitlines()]
    source_classes = json.loads((workspace / "source-classes.json").read_text())
    store = FieldStore(workspace / "field")
    verified = 0
    for row, hidden, prediction in zip(public, gold, predictions):
        loaded = store.load("tenant-a", row["reality"])
        policy_raw = json.loads((workspace / "policies" / f"{hidden['policy']}.json").read_text())
        policy = CompiledPolicy(policy_raw["policy_id"], policy_raw["revision"], tuple(PolicyInstruction(**item) for item in policy_raw["instructions"]), policy_raw["hash"])
        assumptions = tuple(atom.atom_id for atom in loaded.atoms if atom.expression == "seed")
        expected = expected_outcome(loaded.atoms, loaded.factors, assumptions, row["query_expression"], "Prop", policy, source_classes)
        verified += int(prediction["disposition"] == expected["disposition"] and prediction["selected_candidate_id"] == expected["selected_candidate_id"])
    report = {"evaluator_pid": __import__("os").getpid(), "cases": len(predictions), "oracle_agreement": verified / len(predictions) if predictions else 0.0, "runtime_optimizer_imported": "parasite_l8.optimizer" in sys.modules}
    (workspace / "evaluator-process.json").write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["oracle_agreement"] == 1.0 and not report["runtime_optimizer_imported"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
