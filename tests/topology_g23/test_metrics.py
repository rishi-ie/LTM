from dataclasses import replace

from topology_g23.dataset import generate_sentence_examples
from topology_g23.metrics import sentence_metrics
from topology_g23.schemas import SentenceCompilationResult, TopologyHypothesis


def test_semantic_metrics_ignore_temporary_span_ids():
    example = next(item for item in generate_sentence_examples("development") if item.gold.disposition == "accept")
    renamed = {span.candidate_id: f"runtime-{index}" for index, span in enumerate(example.gold.spans)}
    spans = tuple(replace(span, candidate_id=renamed[span.candidate_id]) for span in example.gold.spans)
    relations = tuple(
        replace(
            relation,
            role_candidate_ids=tuple(
                (role, tuple(renamed[item] for item in ids))
                for role, ids in relation.role_candidate_ids
            ),
        )
        for relation in example.gold.relations
    )
    hypothesis = TopologyHypothesis("runtime", spans, relations, "accept", 1.0, 1.0)
    result = SentenceCompilationResult(example.source.source_id, (hypothesis,), None, "accept", (), 0.0, 8)

    metrics = sentence_metrics((example,), (result,))

    assert metrics["all_case_exact"] == 1.0
    assert metrics["accepted_exact_precision"] == 1.0
    assert metrics["relation_role_exactness"] == 1.0


def test_semantic_metrics_preserve_directional_roles():
    example = next(
        item
        for item in generate_sentence_examples("development")
        if item.gold.relations and item.gold.relations[0].relation_type == "implies"
    )
    relation = example.gold.relations[0]
    first_role, first_ids = relation.role_candidate_ids[0]
    second_role, second_ids = relation.role_candidate_ids[1]
    reversed_relation = replace(
        relation,
        role_candidate_ids=((first_role, second_ids), (second_role, first_ids)),
    )
    hypothesis = TopologyHypothesis("reversed", example.gold.spans, (reversed_relation,), "accept", 1.0, 1.0)
    result = SentenceCompilationResult(example.source.source_id, (hypothesis,), None, "accept", (), 0.0, 8)

    metrics = sentence_metrics((example,), (result,))

    assert metrics["all_case_exact"] == 0.0
    assert metrics["relation_role_exactness"] == 0.0
