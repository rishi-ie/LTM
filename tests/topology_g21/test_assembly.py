from topology_g21.assemble import valid_topology
from topology_g21.dataset import generate_cases
from topology_g21.schemas import ReasoningPrediction


def test_gold_like_prediction_is_topology_valid():
    case = next(c for c in generate_cases("development") if c.gold_relation == "implies")
    prediction = ReasoningPrediction(case.case_id, case.gold_relation, case.gold_direction, case.gold_roles, case.gold_scope, case.gold_disposition, 1.0)
    assert valid_topology(case, prediction)
