from __future__ import annotations

from pathlib import Path

import numpy as np

from ltm_inference_i31.axioms import standard_axiom_bodies
from ltm_inference_i31.dataset import (
    body_from_obj,
    build_split,
    expr_from_obj,
    feature,
    load_rows,
    problem_from_obj,
)
from ltm_inference_i31.detours import build_detour_fixture, shortest_distance
from ltm_inference_i31.field import MathFieldIndex, build_field
from ltm_inference_i31.formal import verify_proof
from ltm_inference_i31.kernel import SearchKernel
from ltm_inference_i31.realities import COUNTERFACTUAL_SUM3, STANDARD, apply_finite_operator
from ltm_inference_i31.runtime import infer
from ltm_inference_i31.schemas import FormalProofStep, MathematicalBody, TheoremProblem


def _field(tmp_path):
    build_split(tmp_path, "development", 4, 13)
    root = tmp_path / "public" / "development"
    bodies = tuple(body_from_obj(item) for item in load_rows(root / "bodies.jsonl"))
    return MathFieldIndex(bodies, np.load(root / "body-vectors.npy"), build_field(bodies, np.load(root / "body-vectors.npy")))


def test_dynamic_content_frontier_opens_later_stage(tmp_path):
    field = _field(tmp_path)
    problem = problem_from_obj(load_rows(tmp_path / "public/development/theorems.jsonl")[0])
    initial = field.content_frontier(problem.source, problem.goal)
    assert initial is not None
    first = field.bodies[initial[0]]
    later = field.content_frontier(first.right, problem.goal)
    assert later is not None
    assert set(initial).isdisjoint(later)
    assert len(initial) <= 64
    assert field.read_count <= 128
    assert field.root.transition_modes
    assert len(field.root.transition_modes) <= 8


def test_exact_body_proof_replays(tmp_path):
    field = _field(tmp_path)
    public = load_rows(tmp_path / "public/development/theorems.jsonl")[0]
    gold = load_rows(tmp_path / "evaluator-gold/development/gold.jsonl")[0]
    problem = problem_from_obj(public)
    proof = tuple(FormalProofStep(str(item["body_id"]), tuple(item["path"]), bool(item["reverse"]), expr_from_obj(item["before"]), expr_from_obj(item["after"])) for item in gold["proof"])
    assert verify_proof(problem.source, problem.goal, proof, field.bodies, problem.reality_key)


def test_counterfactual_operator_table_is_isolated():
    assert apply_finite_operator(STANDARD, 1, 1) == 2
    assert apply_finite_operator(COUNTERFACTUAL_SUM3, 1, 1) == 3
    assert STANDARD.manifest_hash != COUNTERFACTUAL_SUM3.manifest_hash


def test_runtime_cannot_apply_cross_reality_body():
    from ltm_inference_i31.dataset import atom, feature
    from ltm_inference_i31.formal import body_hash

    source, target = atom("field:field:000000:stage00"), atom("field:field:000000:stage01:slot00")
    foreign = MathematicalBody("foreign", "sum3-v1", source, target, "", 0)
    foreign = MathematicalBody(foreign.body_id, foreign.reality_key, foreign.left, foreign.right, body_hash(foreign), 0)
    vectors = np.concatenate((feature(source), feature(target)))[None, :]
    field = MathFieldIndex((foreign,), vectors, build_field((foreign,), vectors))
    result = infer(TheoremProblem("p", "standard-v1", source, target, 64, 2), field, SearchKernel())
    assert result.disposition == "unknown"


def test_public_runtime_does_not_import_evaluator_or_gold():
    source = (Path(__file__).parents[2] / "src/ltm_inference_i31/runtime.py").read_text(encoding="utf-8")
    assert "evaluator" not in source
    assert "evaluator-gold" not in source


def test_signed_standard_axiom_bodies_replay_algebraic_proof():
    from ltm_inference_i3.formal import c, e

    bodies = {item.body_id: item for item in standard_axiom_bodies()}
    source = e("mul", e("add", c(5), c(0)), c(1))
    middle = e("add", c(5), c(0))
    goal = c(5)
    proof = (
        FormalProofStep("standard-v1:axiom:ring.mul_one", (), False, source, middle),
        FormalProofStep("standard-v1:axiom:ring.add_zero", (), False, middle, goal),
    )
    assert verify_proof(source, goal, proof, bodies, "standard-v1")


def test_runtime_constructs_standard_algebra_proof_from_retrieved_axiom_bodies():
    from ltm_inference_i3.formal import c, e
    from ltm_inference_i31.dataset import feature

    bodies = standard_axiom_bodies()
    vectors = np.asarray([np.concatenate((feature(item.left), feature(item.right))) for item in bodies], dtype=np.float32)
    field = MathFieldIndex(bodies, vectors, build_field(bodies, vectors))
    source = e("mul", e("add", c(5), c(0)), c(1))
    result = infer(TheoremProblem("algebra", "standard-v1", source, c(5), 64, 4), field, SearchKernel(), prefer_reductions=True)
    assert result.disposition == "proved"
    assert verify_proof(source, c(5), result.proof, field.bodies, "standard-v1")


def test_detour_fixture_keeps_distance_evaluator_only():
    fixture = build_detour_fixture()
    assert shortest_distance(fixture) == 3
    assert all(not (body.left == fixture.source and body.right == fixture.goal) for body in fixture.bodies)
    assert all("stage" not in str(body.left.value) and "slot" not in str(body.left.value) for body in fixture.bodies)


def test_opaque_body_index_is_bounded_and_query_independent():
    fixture = build_detour_fixture()
    vectors = np.asarray([np.concatenate((feature(item.left), feature(item.right))) for item in fixture.bodies], dtype=np.float32)
    field = MathFieldIndex(fixture.bodies, vectors, build_field(fixture.bodies, vectors))
    assert set(field.content_frontier(fixture.source, fixture.goal) or ()) == {item.body_id for item in fixture.bodies if item.left == fixture.source}
    assert set(field.reverse_frontier(fixture.goal)) == {item.body_id for item in fixture.bodies if item.right == fixture.goal}
