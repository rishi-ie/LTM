from ltm_inference_i1.dataset import generate_bodies, generate_queries


def test_generated_bodies_have_no_reasoning_relation_labels() -> None:
    bodies, units, vectors = generate_bodies("test", 20, 1860)
    queries = generate_queries("test", bodies, units, 20, 1861)
    assert len(vectors) == len(units)
    assert all("relation" not in unit.identity_key for unit in units)
    assert all("gold_candidate_id" in query for query in queries)
    assert {unit.phase_index for unit in units if unit.body_id == bodies[0].body_id} == {0, 1}
