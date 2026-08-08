from __future__ import annotations

from ltm_limit_l3.compiler import compile_body, compile_question, source


def test_registered_binder_and_ground_constant_are_distinct():
    schema = compile_body(source("For every x, x + 0 = x"))
    ground = compile_body(source("5 + 0 = 5"))
    assert schema is not None and schema.axiom_id == "ring.add_zero"
    assert ground is not None and ground.axiom_id == "ring.add_zero"
    assert schema.left != ground.left


def test_open_ended_question_abstains():
    result = compile_question(source("simplify 5 + 0"))
    assert result.disposition == "clarification_required"
    assert result.failure_codes == ("GOAL_DISCOVERY_REQUIRED",)
