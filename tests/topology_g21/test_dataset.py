from topology_g21.dataset import LABELS, ROLE_LABELS, generate_cases


def test_splits_are_balanced_and_disjoint():
    train, locked = generate_cases("train"), generate_cases("locked")
    assert len(train) == 2000 and len(locked) == 1000
    assert {case.gold_relation for case in train} == set(LABELS)
    assert {case.statement for case in train}.isdisjoint({case.statement for case in locked})
    assert all(len(case.arguments) in (2, 3) for case in locked)


def test_roles_are_derived_from_g1_registry():
    assert "premise" in ROLE_LABELS and "conclusion" in ROLE_LABELS and "pad" in ROLE_LABELS
    assert all(case.gold_roles for case in generate_cases("development"))
