import pytest

from ltm_inference_i1.schemas import AtomicMumbrane, InferencePrompt, LatentInferenceResult


def test_runtime_contracts_allow_simple_context_but_no_factual_operations() -> None:
    atom = AtomicMumbrane("u", "b", 0, 0, 0, "positive", "observed", "global", None, None, "entity:e", "source:b")
    prompt = InferencePrompt("p", (atom.unit_id,), "global", None, (atom.unit_id,), 1)
    result = LatentInferenceResult("p", "unknown", (), None, (), 0, 1, (), ())
    assert prompt.clamped_unit_ids == ("u",)
    assert result.factual_operations == ()


def test_bounds_and_invalid_operations_fail_closed() -> None:
    with pytest.raises(ValueError):
        InferencePrompt("p", ("u",), "global", None, tuple(f"u{i}" for i in range(65)), 1)
    with pytest.raises(ValueError):
        LatentInferenceResult("p", "candidate", (), None, (), 0, 0, (), (("forbidden",),))
