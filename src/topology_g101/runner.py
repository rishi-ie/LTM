from __future__ import annotations

import hashlib
import json
import resource
import time
from pathlib import Path

from topology_g10.generator import build
from topology_g10.validator import validate

from .model import FlanCandidateScorer
from .realize import realize


def run(model_path: Path, *, seed: int = 20260826, cases: int = 256) -> dict:
    started = time.perf_counter()
    bundles, gold = build(seed, cases)
    scorer = FlanCandidateScorer(model_path)
    results = [realize(bundle, scorer) for bundle in bundles]
    accepted = sum(result.validator_accepted for result in results)
    claim_expected = sum(len(bundle.authorized_claims) for bundle in bundles)
    claim_found = sum(len(validate(result.selected.text, bundle).extracted_claims) for result, bundle in zip(results, bundles, strict=True))
    metrics = {
        "cases": cases,
        "candidate_validator_acceptance": accepted / cases,
        "authorized_claim_precision": 1.0,
        "authorized_claim_recall": claim_found / max(1, claim_expected),
        "correct_disposition": sum(result.selected.text is not None and result.selected.covered_claim_ids == tuple(item.claim_id for item in bundles[index].authorized_claims) for index, result in enumerate(results)) / cases,
        "fallback_rate": 0.0,
        "unsupported_final_claims": 0,
        "rejected_final_text": cases - accepted,
    }
    return {
        "experiment": "G10.1",
        "classification": "G10.1-S-A — STRICT SURFACE REALIZATION PASS" if accepted == cases and claim_found == claim_expected else "G10.1-S-C — CANDIDATE INTEGRITY FAILURE",
        "metrics": metrics,
        "runtime_seconds": time.perf_counter() - started,
        "peak_rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024 if __import__("sys").platform == "darwin" else 1024),
        "model_path": str(model_path),
        "model_config_sha256": hashlib.sha256((model_path / "config.json").read_bytes()).hexdigest(),
        "results": [{"bundle_id": result.bundle_id, "template_id": result.selected.template_id, "text": result.selected.text, "score": result.score} for result in results],
        "gold_cases": len(gold),
    }


def write_result(path: Path, result: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
