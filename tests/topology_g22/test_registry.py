from topology_g1.registry import REGISTRY
from topology_g22.registry import direction_for, enumerate_legal_candidates
from topology_g22.schemas import SpanProposal


def test_legal_candidates_only_use_registered_relations_and_roles() -> None:
    spans = (
        SpanProposal("s1", "A is ready", "claim", 0, 10, 1.0),
        SpanProposal("s2", "B is safe", "claim", 14, 23, 1.0),
        SpanProposal("s3", "C is sealed", "claim", 28, 39, 1.0),
    )
    candidates = enumerate_legal_candidates(spans)
    assert candidates
    for relation, bindings in candidates:
        assert relation in REGISTRY
        assert {role for role, _ in bindings} == {role.name for role in REGISTRY[relation].roles}


def test_direction_is_derived_not_independently_generated() -> None:
    assert direction_for("conjoins") == "multi_source_to_target"
    assert direction_for("after") == "arg2_to_arg1"
    assert direction_for("excludes") == "symmetric"
