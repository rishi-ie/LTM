"""Read-only semantic replay worker for one historical gap."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def replay(gap: str, workspace: Path) -> dict:
    if gap == "G3":
        from topology_g3.evaluate import verify
        return verify(workspace)
    if gap == "G4":
        from topology_g4.evaluate import verify
        return verify(workspace)
    if gap == "G5":
        from topology_g5.evaluate import verify
        return verify(workspace)
    if gap == "G6":
        from topology_g6.evaluate import verify_run
        return verify_run(workspace)
    if gap == "G7":
        # The historical verifier still names the pre-organization G6 report
        # path.  Replay its semantic body directly without weakening its check.
        from dataclasses import asdict

        from topology_g7.evaluate import config
        from topology_g7.generator import load
        from topology_g7.optimize import reconcile

        stored = json.loads((workspace / "locked-results.json").read_text())
        replayed = [asdict(reconcile(problem, config())) for problem in load(workspace / "locked")]
        original = [row["result"] for row in stored["rows"]]
        return {
            "classification": stored["classification"],
            "identical_results": json.dumps(replayed, sort_keys=True) == json.dumps(original, sort_keys=True),
        }
    if gap == "G8":
        from topology_g8.evaluate import verify_run
        return verify_run(workspace)
    if gap == "G9":
        from topology_g9.evaluate import verify_run
        return verify_run(workspace)
    if gap == "G10":
        from topology_g101.runner import run
        stored = json.loads((workspace / "locked-results.json").read_text())
        current = run(Path(stored["model_path"]).resolve(), cases=stored["gold_cases"])
        return {
            "classification": stored["classification"],
            "identical_results": current["classification"] == stored["classification"] and current["metrics"] == stored["metrics"] and current["results"] == stored["results"],
        }
    if gap == "G11":
        from topology_g11.evaluate import verify_run
        return verify_run(workspace)
    if gap == "G12":
        from topology_g12.evaluate import verify_run
        return verify_run(workspace)
    if gap == "G13":
        from topology_g13.evaluate import _run_scale, load_cases, scales, settings
        prior = json.loads((workspace / "locked-results.json").read_text())
        config = settings(); root = workspace / "locked"; scale = scales(config)[-1]
        stage = _run_scale(root, scale, config, load_cases(root / "runtime" / "cases.json"), "identity")
        old = {row["query_id"]: row["conclusion"] for row in next(item for item in prior["stages"] if item["scale"] == "S4" and item["layout"] == "identity")["cold"]}
        new = {row["query_id"]: row["conclusion"] for row in stage["cold"]}
        return {"classification": prior["classification"], "identical_results": old == new}
    if gap == "G14":
        from topology_g14.evaluate import _gold, _metrics, _run
        from topology_g14.generator import load_queries
        prior = json.loads((workspace / "core-results.json").read_text())
        current = _metrics(_run(load_queries(workspace / "locked")), _gold(workspace / "locked"))

        def semantic(value: dict) -> dict:
            return {name: {key: item[key] for key in ("accuracy", "required_factor_recall", "full_scans")} for name, item in value.items()}

        return {"classification": prior["controlled_architecture"], "identical_results": semantic(prior["metrics"]) == semantic(current)}
    raise ValueError(f"unsupported replay {gap}")


if __name__ == "__main__":
    print(json.dumps(replay(sys.argv[1], Path(sys.argv[2]).resolve()), sort_keys=True))
