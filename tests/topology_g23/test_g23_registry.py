from topology_g23.registry import RELATION_LABELS, enumerate_legal_candidates
from topology_g23.schemas import TypedSpanCandidate


def test_registry_is_g1_derived_and_directional_candidates_are_legal():
    assert "implies" in RELATION_LABELS
    spans = (TypedSpanCandidate("a", "a", 0, 1, "claim", 1.0, 1.0), TypedSpanCandidate("b", "b", 2, 3, "claim", 1.0, 1.0))
    candidates = enumerate_legal_candidates(spans)
    assert any(item[0] == "implies" for item in candidates)


def test_candidate_pruning_keeps_a_quota_for_each_legal_relation():
    spans = (
        TypedSpanCandidate("a", "a", 0, 1, "claim", 1.0, 1.0),
        TypedSpanCandidate("b", "b", 2, 3, "claim", 1.0, 1.0),
        TypedSpanCandidate("scope", "scope", 4, 9, "scope", 0.2, 0.2),
    )
    candidates = enumerate_legal_candidates(spans)
    relations = {relation for relation, _roles, _score in candidates}
    assert "implies" in relations
    assert "requires" in relations
    assert "excludes" in relations
