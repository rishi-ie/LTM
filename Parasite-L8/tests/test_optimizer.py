from __future__ import annotations

from types import SimpleNamespace

from parasite_l8.optimizer import solve_policy_equilibrium
from parasite_l8.policy import compile_policy


def _fixture():
    atoms = (
        SimpleNamespace(atom_id="seed", expression="seed", sort="Prop"),
        SimpleNamespace(atom_id="yes", expression="goal", sort="Prop"),
        SimpleNamespace(atom_id="no", expression="goal", sort="Prop"),
    )
    factors = (
        SimpleNamespace(body_id="b-yes", input_atom_ids=("seed",), outcome_atom_id="yes", outcome_polarity=1, authority=.8, confidence=1., base_weight=1., independent_source_key="s-yes", scope_key="global", valid_from=None, valid_to=None, weight=.8),
        SimpleNamespace(body_id="b-no", input_atom_ids=("seed",), outcome_atom_id="no", outcome_polarity=-1, authority=.7, confidence=1., base_weight=1., independent_source_key="s-no", scope_key="global", valid_from=None, valid_to=None, weight=.7),
    )
    return atoms, factors


def test_policy_changes_winner_without_answer_propagation() -> None:
    atoms, factors = _fixture()
    support = compile_policy("support", [{"opcode": "source_multiplier", "value": {"support": 1.5, "opposition": .5}}])
    oppose = compile_policy("oppose", [{"opcode": "source_multiplier", "value": {"support": .5, "opposition": 1.5}}])
    kwargs = {"atoms": atoms, "factors": factors, "assumptions": ("seed",), "query_expression": "goal", "query_sort": "Prop", "source_classes": {"s-yes": "support", "s-no": "opposition"}}
    left = solve_policy_equilibrium(policy=support, **kwargs)
    right = solve_policy_equilibrium(policy=oppose, **kwargs)
    assert left.selected_candidate_id != right.selected_candidate_id
    assert left.trajectory and right.trajectory
    assert left.factual_operations == ()


def test_conjunction_requires_all_inputs() -> None:
    atoms = tuple(SimpleNamespace(atom_id=x, expression=e, sort="Prop") for x, e in (("a", "a"), ("b", "b"), ("out", "goal")))
    factor = SimpleNamespace(body_id="and", input_atom_ids=("a", "b"), outcome_atom_id="out", outcome_polarity=1, authority=1., confidence=1., base_weight=1., independent_source_key="s", scope_key="global", valid_from=None, valid_to=None, weight=1.)
    policy = compile_policy("all", [])
    result = solve_policy_equilibrium(atoms, (factor,), assumptions=("a",), query_expression="goal", query_sort="Prop", policy=policy)
    assert result.disposition == "unknown"
