from topology_g22.dataset import generate_sentence_examples
from topology_g22.metrics import sentence_metrics
from topology_g22.schemas import SentenceFragment


def test_perfect_fragment_metric_is_exact() -> None:
    examples = generate_sentence_examples("development")[:12]
    gold = tuple(item.gold for item in examples)
    predictions = tuple(SentenceFragment(item.source, item.disposition, item.spans, item.relations, None, None, "x", 1.0) for item in gold)
    values = sentence_metrics(gold, predictions)
    assert values["all_case_exact"] == 1.0
    assert values["safe_coverage"] == 1.0
