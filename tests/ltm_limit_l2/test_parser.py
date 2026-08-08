from __future__ import annotations

from ltm_limit_l2.compiler import compile_question, compile_statement, source


def test_arithmetic_precedence_and_parentheses():
    result = compile_question(source("(x + 0) * 1 = x"))
    assert result.disposition == "accept"
    assert result.source_expression is not None
    assert result.source_expression.op == "mul"
    assert result.goal_expression.value == "?x"


def test_textual_math_is_conservatively_normalized():
    result = compile_question(source("prove that 5 plus 0 equals 5"))
    assert result.disposition == "accept"
    assert result.source_expression.op == "add"


def test_open_ended_goal_does_not_enter_proof_search():
    result = compile_question(source("simplify (x + 0)"))
    assert result.disposition == "clarification_required"
    assert result.failure_codes == ("GOAL_DISCOVERY_REQUIRED",)


def test_custom_statement_requires_confirmation():
    preview = compile_statement(source("x + 2 = y", reality_key="custom-v1"))
    assert preview.disposition == "clarification_required"
    assert preview.activation_state == "pending_confirmation"
    active = compile_statement(source("x + 2 = y", reality_key="custom-v1"), confirmed=True)
    assert active.disposition == "accept"
    assert active.body is not None


def test_unsupported_symbols_fail_closed():
    result = compile_question(source("x + 0 = x;"))
    assert result.disposition == "clarification_required"
    assert result.failure_codes == ("unsupported mathematical token",)
