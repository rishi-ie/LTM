from topology_g22.preprocess import normalize, split_sentences


def test_sentence_splitting_is_deterministic_and_preserves_document_offsets() -> None:
    document = "  Qorim is ready.  Bastel is safe! "
    sentences = split_sentences("d1", document, "s1")
    assert [item.text for item in sentences] == ["Qorim is ready.", "Bastel is safe!"]
    assert document[sentences[1].source_start:sentences[1].source_end] == "Bastel is safe!"
    assert normalize(" a   b ") == "a b"
