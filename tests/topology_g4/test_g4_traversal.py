from topology_g4.generator import build_dataset
from topology_g4.indexes import FactorIndexes
from topology_g4.schemas import TraversalRequest
from topology_g4.traverse import build_frontier


def _request(row):
    return TraversalRequest(**{**row, "starting_entity_ids": tuple(row["starting_entity_ids"]), "starting_predicate_ids": tuple(row["starting_predicate_ids"])})


def test_chain_frontier_recovers_required_factors():
    factors, requests, gold = build_dataset(7, 1000, 6)
    request = _request(requests[0]); frontier = build_frontier(request, FactorIndexes(factors))
    assert set(gold[0]["required_factor_ids"]).issubset(frontier.exact_factor_ids)
    assert frontier.budget_exhausted is False


def test_conjunction_opens_all_sources():
    factors, requests, gold = build_dataset(7, 1000, 6)
    request = _request(requests[1]); frontier = build_frontier(request, FactorIndexes(factors))
    assert set(gold[1]["required_factor_ids"]).issubset(frontier.exact_factor_ids)
