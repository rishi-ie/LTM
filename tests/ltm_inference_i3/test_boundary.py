from __future__ import annotations

from pathlib import Path

from ltm_inference_i3.formal import standard_axioms, v
from ltm_inference_i3.runtime import infer
from ltm_inference_i3.schemas import FormalProposition, TheoremProblem


def test_runtime_has_no_evaluator_or_gold_reference() -> None:
    source = (Path(__file__).parents[2] / "src" / "ltm_inference_i3" / "runtime.py").read_text(encoding="utf-8")
    assert "evaluator-gold" not in source
    assert "evaluator" not in source


def test_negative_assumption_refutes_without_a_positive_proof() -> None:
    left, right = v("left"), v("right")
    problem = TheoremProblem("refuted", (FormalProposition("neq", left, right),), FormalProposition("eq", left, right), "standard-v1", 64, 8)
    # The test deliberately does not need a learned checkpoint: negative exact
    # evidence is resolved before the latent proposal stage.
    result = infer(problem, standard_axioms(), object())  # type: ignore[arg-type]
    assert result.disposition == "refuted"
    assert not result.proof
