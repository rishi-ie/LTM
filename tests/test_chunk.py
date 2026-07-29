"""Chunk boundaries rely on tokenizer offsets, never decoded token IDs."""

from ltm_poc.chunk import chunk_records
from ltm_poc.config import WorkspaceConfig
from ltm_poc.schemas import TextRecord


class CharacterTokenizer:
    def __call__(self, text, return_offsets_mapping=False, **_kwargs):
        offsets = [(index, index + 1) for index in range(len(text))]
        result = {"input_ids": list(range(len(text)))}
        if return_offsets_mapping:
            result["offset_mapping"] = offsets
        return result


def config() -> WorkspaceConfig:
    return WorkspaceConfig(
        embedding_model_path="embed",
        embedding_model_id="embed",
        embedding_revision="pin",
        decoder_model_path="decode",
        decoder_model_id="decode",
        decoder_revision="pin",
    )


def record(text: str) -> TextRecord:
    return TextRecord(
        record_id="source.txt::000000",
        source_path="source.txt",
        source_kind="text",
        text=text,
        metadata={},
        content_hash="hash",
    )


def test_128_token_window_has_24_token_overlap() -> None:
    chunks = chunk_records([record("a" * 200)], CharacterTokenizer(), config())

    assert [(chunk.token_start, chunk.token_end) for chunk in chunks] == [
        (0, 128),
        (104, 200),
    ]
    assert chunks[0].text[-24:] == chunks[1].text[:24]


def test_unicode_and_empty_records_keep_exact_spans() -> None:
    chunks = chunk_records(
        [record("é\n猫"), record("")], CharacterTokenizer(), config()
    )

    assert len(chunks) == 1
    assert chunks[0].text == "é\n猫"
    assert (chunks[0].char_start, chunks[0].char_end) == (0, 3)
