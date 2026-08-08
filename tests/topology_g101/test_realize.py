from __future__ import annotations

from topology_g10.generator import build
from topology_g10.validator import validate
from topology_g101.grammar import candidates
from topology_g101.realize import realize
from topology_g101.schemas import answer_mr


class FakeScorer:
    def score(self, _mr: str, candidate: str) -> tuple[float, int, float]:
        return (-len(candidate), len(candidate.split()), 0.0)


def test_every_generated_candidate_is_semantically_valid() -> None:
    bundles, _ = build(20260826, 64)
    for bundle in bundles:
        mr = answer_mr(bundle)
        assert candidates(bundle, mr)
        assert all(validate(item.text, bundle).accepted for item in candidates(bundle, mr))


def test_realizer_only_returns_a_prevalidated_candidate() -> None:
    bundles, _ = build(20260826, 64)
    for bundle in bundles:
        result = realize(bundle, FakeScorer())
        assert result.validator_accepted
        assert validate(result.selected.text, bundle).accepted
