from __future__ import annotations

from topology_g9.controls import no_coverage
from topology_g9.generator import ATTACKS, build
from topology_g9.verifier import verify


def settings() -> dict:
    return {"topology_version": "topology-v1", "field_version": "field-v1"}


def test_valid_bundles_and_each_registered_corruption_are_distinguished() -> None:
    bundles, gold = build(1729, len(ATTACKS), settings())
    for bundle in bundles:
        result = verify(bundle)
        expected = gold[bundle.bundle_id]
        assert result.status == expected["status"]
        assert result.failure_codes == (() if expected["failure"] is None else (expected["failure"],))


def test_coverage_control_accepts_only_the_coverage_attack() -> None:
    bundles, gold = build(1729, len(ATTACKS), settings())
    coverage = next(bundle for bundle in bundles if gold[bundle.bundle_id]["failure"] == "INSUFFICIENT_COVERAGE")
    assert verify(coverage).status == "rejected"
    assert no_coverage(coverage).status != "rejected"


def test_unknown_and_conflict_are_valid_outcomes() -> None:
    bundles, gold = build(1729, len(ATTACKS), settings())
    statuses = {verify(bundle).status for bundle in bundles if gold[bundle.bundle_id]["failure"] is None}
    assert {"verified", "unknown", "verified_with_tension"}.issubset(statuses)
