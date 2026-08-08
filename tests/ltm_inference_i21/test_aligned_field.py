from __future__ import annotations

from ltm_inference_i21.dataset import generate_bodies, generate_queries
from ltm_inference_i21.field import AlignedField
from ltm_inference_i21.kernel import AlignedTransitionKernel, infer
from ltm_inference_i21.schemas import DynamicPrompt, InferenceResult


def test_runtime_result_never_contains_factual_operations() -> None:
    result = InferenceResult("p", "unknown", None, (), (), (), "certified")
    assert result.factual_operations == ()


def test_public_queries_hide_answer_and_path() -> None:
    bodies, units, _ = generate_bodies("test", 128, 17)
    query = generate_queries("test", bodies, units, 1, 18)[0]
    public = {key: value for key, value in query.items() if key not in {"gold_candidate_id", "required_body_ids", "depth", "query_type", "initial_entity"}}
    assert "gold_candidate_id" not in public
    assert "required_body_ids" not in public


def test_aligned_same_body_frontier_and_terminal_completion() -> None:
    bodies, units, vectors = generate_bodies("test", 512, 19)
    field = AlignedField(bodies, units, vectors)
    model = AlignedTransitionKernel()
    field.refresh(model)
    source = next(unit for unit in units if unit.identity_key.endswith("state:60") and unit.phase_index == 0)
    prompt = DynamicPrompt("p", (source.unit_id,), source.scope_key, 64, 64)
    result = infer(model, field, prompt)
    assert result.disposition == "candidate"
    assert result.selected_candidate_id is not None
    assert field.units[result.selected_candidate_id].identity_key.endswith("state:64")
    assert len(result.visited_body_ids) == 4
    entities = {field.body_source_units[body_id].identity_key.split("|", 1)[0] for body_id in result.visited_body_ids}
    assert len(entities) == 4
