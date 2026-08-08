from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "validation"))

from p1_common import build_suite
from p1_evaluator import _oracle, score


def test_p1_suite_is_fresh_opaque_and_complete():
    cases = build_suite()
    assert len(cases) == 72
    forbidden = {"expected", "certificate", "route", "required_body_ids", "evaluator"}
    for case in cases:
        public = case.public()
        assert not forbidden.intersection(public)
        assert all(token not in repr(public).lower() for token in ("expected_depth", "proof_path"))
        assert "expected" not in public["request"]


def test_independent_oracle_covers_unique_alternative_and_unknown():
    cases = [case for case in build_suite() if case.track == "equilibrium"]
    gold = []
    for case in cases:
        expected = _oracle(case.public())
        expected["case_id"] = case.case_id
        gold.append(expected)
    scored = score(gold, gold)
    assert scored["exactness"] == 1.0
    assert any(row["disposition"] == "alternatives" for row in gold)
    assert any(row["disposition"] == "unknown" for row in gold)


def test_scorer_rejects_wrong_candidate():
    cases = [case for case in build_suite() if case.track == "equilibrium"][:1]
    gold = [_oracle(cases[0].public()) | {"case_id": cases[0].case_id}]
    wrong = [{"case_id": cases[0].case_id, "disposition": "candidate", "claim": "invented"}]
    scored = score(gold, wrong)
    assert scored["exactness"] == 0.0
    assert scored["incorrect_accepted"] == 1
