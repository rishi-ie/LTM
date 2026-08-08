from __future__ import annotations

from ltm_limit_l3.generator import grounded_case, locked_suite, mixed_case, unknown_case


def test_grounded_and_mixed_cases_have_forty_five_compiled_bodies():
    grounded = grounded_case(45, 2)
    mixed = mixed_case(45, 2)
    assert len(grounded.bodies) == 45
    assert len(mixed.bodies) == 45
    assert len({body.axiom_id for body in mixed.bodies}) >= 8
    assert grounded.certificate.shortest_depth == 45


def test_locked_suite_is_one_field_with_isolated_unknown_requests():
    suite = locked_suite(grounded_cases=2, mixed_cases=1, safety_cases=2, field_size=200, depth=45)
    assert len(suite.bodies) == 200
    assert len(suite.grounded) == 2
    assert len(suite.mixed) == 1
    assert all(not item.body_ids for item in suite.safety)
    assert unknown_case(3).question.disposition == "accept"
