from topology_g22.dataset import (
    LINK_COUNTS,
    SENTENCE_COUNTS,
    generate_link_examples,
    generate_sentence_examples,
    runtime_sentence_dict,
)


def test_exact_configured_split_sizes_and_runtime_gold_separation() -> None:
    for split in ("train", "development", "locked"):
        examples = generate_sentence_examples(split)
        assert len(examples) == sum(SENTENCE_COUNTS[split])
        assert len(generate_link_examples(split)) == LINK_COUNTS[split]
        runtime = runtime_sentence_dict(examples[0])
        assert "gold" not in runtime and "template_id" not in runtime


def test_offsets_reproduce_each_gold_span() -> None:
    for example in generate_sentence_examples("development")[:50]:
        for span in example.gold.spans:
            assert example.source.text[span.start:span.end] == span.text
