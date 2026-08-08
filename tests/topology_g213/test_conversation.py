from topology_g213.dataset import generate
from topology_g213.registry import ACTIONS, ACTS


def test_dataset_has_all_conversation_families():
    cases = generate("development")
    assert len(cases) == 2400
    assert {case.act for case in cases} == set(ACTS)
    assert {case.action for case in cases} == set(ACTIONS)
    assert sum(case.reference_state == "ambiguous" for case in cases) == 200


def test_unsafe_cases_are_not_factual_claims():
    cases = generate("development")
    assert all(case.disposition == "quarantine" for case in cases if "evaluator-only" in case.source.text)
