"""Hashable corpus materialization for the development and locked builders."""

from __future__ import annotations

import hashlib
import json
import pickle
from dataclasses import asdict
from pathlib import Path

from .schemas import L3EvaluatorExpectation, L3LockedSuite, L3Problem, MathCorpusManifest


def materialize(workspace: Path, problems: tuple[L3Problem, ...], field_size: int = 50000) -> MathCorpusManifest:
    root = workspace / "corpus"
    root.mkdir(parents=True, exist_ok=True)
    bodies = {body.body_id: body for problem in problems for body in problem.bodies}
    path = root / "bodies.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for body in sorted(bodies.values(), key=lambda item: item.body_id):
            handle.write(json.dumps({
                "body_id": body.body_id,
                "reality_key": body.reality_key,
                "axiom_id": body.axiom_id,
                "direction_policy": body.direction_policy,
                "source_text": body.source_text,
                "source_hash": body.source_hash,
                "body_hash": body.body_hash,
            }, sort_keys=True) + "\n")
    archive_payload = tuple((body.body_id, body.source_text, body.source_hash) for body in sorted(bodies.values(), key=lambda item: item.body_id))
    archive_hash = hashlib.sha256(repr(archive_payload).encode()).hexdigest()
    return MathCorpusManifest("standard-v1", len(bodies), field_size, hashlib.sha256(path.read_bytes()).hexdigest(), archive_hash)


def manifest_dict(manifest: MathCorpusManifest) -> dict[str, object]:
    return asdict(manifest)


def materialize_locked(workspace: Path, suite: L3LockedSuite) -> MathCorpusManifest:
    """Write public sources and evaluator expectations without mixing them."""
    root = workspace / "locked"
    root.mkdir(parents=True, exist_ok=True)
    archive = root / "source-archive.jsonl"
    with archive.open("w", encoding="utf-8") as handle:
        for body in suite.bodies:
            handle.write(json.dumps({
                "body_id": body.body_id,
                "reality_key": body.reality_key,
                "source_text": body.source_text,
                "source_hash": body.source_hash,
                "body_hash": body.body_hash,
            }, sort_keys=True) + "\n")
    public = root / "public-cases.jsonl"
    with public.open("w", encoding="utf-8") as handle:
        for case in (*suite.grounded, *suite.mixed, *suite.safety):
            handle.write(json.dumps({
                "case_id": case.case_id,
                "panel": case.panel,
                "question": case.question.source.text,
                "question_source_id": case.question.source.source_id,
                "reality_key": case.question.source.reality_key,
            }, sort_keys=True) + "\n")
    evaluator = tuple(
        L3EvaluatorExpectation(
            case.case_id,
            case.panel,
            "unknown" if case.panel == "safety" else "proved",
            None if case.panel == "safety" else case.expected_depth,
            case.body_ids,
            case.certificate.certificate_hash,
        )
        for case in (*suite.grounded, *suite.mixed, *suite.safety)
    )
    evaluator_path = root / "evaluator-expectations.json"
    evaluator_path.write_text(json.dumps([asdict(item) for item in evaluator], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    # This is an ignored build cache.  It contains compiled ASTs, not a second
    # source of truth; public inputs are reconstructed from the JSON archives.
    with (root / "compiled-suite.pkl").open("wb") as handle:
        pickle.dump(suite, handle, protocol=pickle.HIGHEST_PROTOCOL)
    archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
    return MathCorpusManifest("standard-v1", len(suite.bodies), len(suite.bodies), suite.suite_hash, archive_hash)


def load_locked(workspace: Path) -> L3LockedSuite:
    path = workspace / "locked" / "compiled-suite.pkl"
    if not path.exists():
        raise FileNotFoundError("LOCKED_SUITE_MISSING")
    with path.open("rb") as handle:
        suite = pickle.load(handle)
    if not isinstance(suite, L3LockedSuite):
        raise TypeError("LOCKED_SUITE_SCHEMA_MISMATCH")
    return suite
