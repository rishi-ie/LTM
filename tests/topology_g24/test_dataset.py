from topology_g1.registry import validate_relation
from topology_g24.dataset import generate_examples
from topology_g24.program import assemble_program


def test_dataset_has_exact_split_distribution_and_g1_valid_accepted_programs():
    examples = generate_examples("development")

    assert len(examples) == 2000
    assert sum(item.gold.disposition == "accept" for item in examples) == 1600
    assert sum(item.gold.disposition == "clarification_required" for item in examples) == 200
    assert sum(item.gold.disposition == "quarantine" for item in examples) == 200
    for example in examples:
        assembled = assemble_program(example.source, example.gold)
        if example.gold.disposition == "accept":
            assert assembled is not None
            for relation in assembled.g1_relations:
                validate_relation(relation, {node.node_id: node for node in assembled.g1_nodes})
        else:
            assert assembled is None


def test_dataset_relation_coverage_is_g1_complete():
    examples = generate_examples("development")
    relations = {item.gold.operators[0].relation_type for item in examples if item.gold.operators}

    assert len(relations) == 18
