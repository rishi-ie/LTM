from __future__ import annotations

from ltm_inference_i3.dataset import _expand
from ltm_inference_i3.formal import e, standard_axioms, v, verify_proof
from ltm_inference_i3.schemas import FormalProposition


def test_standard_inventory_is_frozen_at_46_schemas() -> None:
    axioms = standard_axioms()
    assert len(axioms) == 46
    assert len({item.axiom_id for item in axioms}) == 46
    assert {item.family for item in axioms} == {"equality", "ring", "order", "modular", "sets", "logic"}


def test_backward_generated_trace_replays_forward() -> None:
    schemas = {item.axiom_id: item for item in standard_axioms()}
    goal = v("example")
    start, trace = _expand(goal, "ring", 6, __import__("random").Random(4), schemas)
    assert len(trace) >= 2
    assert verify_proof(FormalProposition("eq", start, goal), trace, schemas)


def test_wrong_path_or_corrupt_step_fails_replay() -> None:
    schemas = {item.axiom_id: item for item in standard_axioms()}
    goal = v("example")
    start, trace = _expand(goal, "logic", 4, __import__("random").Random(5), schemas)
    broken = trace[:-1]
    assert not verify_proof(FormalProposition("eq", start, goal), broken, schemas)


def test_equality_substitution_can_expand_and_replay() -> None:
    schemas = {item.axiom_id: item for item in standard_axioms()}
    goal = v("equality")
    start, trace = _expand(goal, "equality", 4, __import__("random").Random(7), schemas)
    assert len(trace) == 4
    assert verify_proof(FormalProposition("eq", start, goal), trace, schemas)


def test_order_axioms_expand_backward_and_replay_forward() -> None:
    schemas = {item.axiom_id: item for item in standard_axioms()}
    goal = e("lt", v("left"), v("right"))
    start, trace = _expand(goal, "order", 4, __import__("random").Random(8), schemas)
    assert len(trace) == 4
    assert verify_proof(FormalProposition("eq", start, goal), trace, schemas)
