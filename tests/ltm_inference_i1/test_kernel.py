import numpy as np

from ltm_inference_i1.dataset import generate_bodies, generate_queries
from ltm_inference_i1.index import BodyIndex
from ltm_inference_i1.kernel import PairPotential, infer
from ltm_inference_i1.schemas import InferencePrompt


def test_optimizer_is_bounded_and_emits_soft_only_result() -> None:
    bodies, units, vectors = generate_bodies("test", 32, 1860)
    queries = generate_queries("test", bodies, units, 1, 1861)
    row = queries[0]
    prompt = InferencePrompt(row["prompt_id"], row["clamped_unit_ids"], "global", None, row["candidate_atom_ids"], 32)
    result = infer(PairPotential(), BodyIndex(bodies, units, vectors), vectors, prompt, confidence=.0, margin_threshold=-1.0)
    assert len(result.trajectory) == 9
    assert result.bodies_visited <= 32
    assert result.units_visited <= len(units)
    assert result.factual_operations == ()
    assert np.all(np.isfinite([step.energy for step in result.trajectory]))
