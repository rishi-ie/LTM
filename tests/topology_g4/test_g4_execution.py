from topology_g4.execute import execute
from topology_g4.generator import build_dataset
from topology_g4.schemas import TraversalRequest


def test_exception_overrides_positive_path():
    factors, requests, gold = build_dataset(7, 1000, 6)
    request = TraversalRequest(**{**requests[4], "starting_entity_ids": tuple(requests[4]["starting_entity_ids"]), "starting_predicate_ids": tuple(requests[4]["starting_predicate_ids"])})
    relevant = tuple(item for item in factors if item.factor_id in gold[4]["required_factor_ids"])
    assert execute(request, relevant).conclusion == "contradicted"
