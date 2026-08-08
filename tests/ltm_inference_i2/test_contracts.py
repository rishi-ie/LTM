import numpy as np
import pytest

from ltm_inference_i2.schemas import (
    DynamicInferencePrompt,
    DynamicInferenceResult,
    LatentFieldState,
)


def test_prompt_has_no_candidate_list_and_state_is_128d():
    prompt = DynamicInferencePrompt("p", ("u",), "global", None, 32, 64)
    assert prompt.maximum_bodies == 64
    state = LatentFieldState(tuple(float(v) for v in np.zeros(128)), (), (), "0" * 64)
    assert len(state.semantic_position) == 128


def test_factual_operations_fail_closed():
    DynamicInferencePrompt("p", ("u",), "global", None, 1, 1)
    state = LatentFieldState(tuple(float(v) for v in np.zeros(128)), (), (), "0" * 64)
    with pytest.raises(ValueError):
        DynamicInferenceResult("p", "unknown", state, state, (), None, (), (), (), "incomplete_frontier", (), ("bad",))
