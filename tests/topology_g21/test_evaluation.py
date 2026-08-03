from topology_g21.dataset import generate_cases
from topology_g21.metrics import score
from topology_g21.schemas import ReasoningPrediction


def test_perfect_predictions_score_perfectly():
    cases = generate_cases("development")[:20]
    predictions = tuple(ReasoningPrediction(c.case_id, c.gold_relation, c.gold_direction, c.gold_roles, c.gold_scope, c.gold_disposition, 1.0) for c in cases)
    result = score(cases, predictions)
    assert result["relation_accuracy"] == result["topology_agreement"] == 1.0
