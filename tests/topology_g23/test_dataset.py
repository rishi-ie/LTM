from topology_g23.dataset import generate_link_examples, generate_sentence_examples


def test_exact_split_sizes_and_dispositions():
    examples = generate_sentence_examples("development")
    assert len(examples) == 2000
    assert sum(item.gold.disposition == "accept" for item in examples) == 1600
    assert sum(item.gold.disposition == "clarification_required" for item in examples) == 200
    assert sum(item.gold.disposition == "quarantine" for item in examples) == 200


def test_sources_have_exact_hashes_and_links_are_bounded():
    examples = generate_link_examples("development")
    assert len(examples) == 1000
    assert all(1 <= len(item.public_candidates) <= 16 for item in examples)
    assert all(item.source.source_hash for item in examples)
