from ltm_inference_i2.dataset import generate_bodies
from ltm_inference_i2.index import FieldIndex, build_cells
from ltm_inference_i2.kernel import TransitionKernel, infer
from ltm_inference_i2.schemas import DynamicInferencePrompt


def test_prompt_anchor_is_fixed_and_result_is_soft():
    bodies, units, vectors = generate_bodies("test", 256, 1871)
    cells, summary = build_cells(bodies, units, vectors)
    index = FieldIndex(bodies, units, vectors, cells, summary)
    first = next(unit for unit in units if unit.phase_index == 0)
    prompt = DynamicInferencePrompt("p", (first.unit_id,), "global", None, 4, 16)
    result = infer(TransitionKernel(), index, vectors, prompt, 0.1, 0.0)
    assert result.initial_state.semantic_position == result.initial_state.semantic_position
    assert not result.factual_operations
    assert result.trajectory
