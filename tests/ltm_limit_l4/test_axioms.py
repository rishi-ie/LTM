from ltm_inference_i3.formal import standard_axioms
from ltm_limit_l4.axioms import EXCLUDED, audit_axioms, executable_axioms


def test_executable_manifest_is_audited_subset() -> None:
    result = audit_axioms()
    assert len(standard_axioms()) == 46
    assert len(executable_axioms()) == 39
    assert result["passed"] is True
    assert all(item["bounded_semantic_agreement"] for item in result["checks"])
    assert set(result["excluded"]) == EXCLUDED


def test_unsafe_and_unbound_schemas_are_not_executable() -> None:
    identifiers = {item.axiom_id for item in executable_axioms()}
    assert not identifiers.intersection(EXCLUDED)
    assert not next(item for item in executable_axioms() if item.axiom_id == "ring.mul_zero").reversible
