from ltm_inference_i3.formal import expression_size
from ltm_limit_l4.codec import problem_from_obj, step_from_obj
from ltm_limit_l4.generator import _problem
from ltm_limit_l4.schemas import FORBIDDEN_PUBLIC_FIELDS


def test_public_problem_contains_no_evaluator_fields() -> None:
    public, gold = _problem("test", 4, 9, depth=4, branching=16, family="sets")
    assert not set(public).intersection(FORBIDDEN_PUBLIC_FIELDS)
    assert gold["depth"] == 4
    assert gold["source_goal_component_distance"] == 4


def test_paired_goals_share_source_but_require_different_first_actions() -> None:
    left, left_gold = _problem("pair", 0, 11, depth=4, branching=16, family="ring", pair_side=0)
    right, right_gold = _problem("pair", 1, 11, depth=4, branching=16, family="ring", pair_side=1)
    assert problem_from_obj(left).source == problem_from_obj(right).source
    assert problem_from_obj(left).goal != problem_from_obj(right).goal
    assert step_from_obj(left_gold["proof"][0]).application.site_path != step_from_obj(right_gold["proof"][0]).application.site_path


def test_detour_panel_contains_a_size_increasing_exact_step() -> None:
    _, gold = _problem("detour", 0, 13, depth=4, branching=8, family="ring", detour=True)
    proof = tuple(step_from_obj(item) for item in gold["proof"])
    assert any(expression_size(step.after) > expression_size(step.before) for step in proof)
