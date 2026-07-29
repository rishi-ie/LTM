"""Payload/vector alignment and integrity checks."""

import numpy as np
import pytest

from ltm_poc.config import WorkspaceConfig
from ltm_poc.schemas import ChunkRecord
from ltm_poc.store import CorpusStore


def config() -> WorkspaceConfig:
    return WorkspaceConfig(
        embedding_model_path="embed",
        embedding_model_id="embed",
        embedding_revision="pin",
        decoder_model_path="decode",
        decoder_model_id="decode",
        decoder_revision="pin",
    )


def chunk() -> ChunkRecord:
    return ChunkRecord(
        chunk_id="r::chunk-000000",
        record_id="r",
        source_path="source.txt",
        source_kind="text",
        text="payload",
        char_start=0,
        char_end=7,
        token_start=0,
        token_end=1,
        token_count=1,
        content_hash="hash",
        metadata={},
    )


def test_store_round_trips_and_detects_tampering(tmp_path) -> None:
    store = CorpusStore(tmp_path)
    vectors = np.zeros((1, 384), dtype=np.float32)
    manifest = store.write([chunk()], vectors, config())

    chunks, loaded_vectors, loaded_manifest = store.read()
    assert chunks[0].chunk_id == "r::chunk-000000"
    assert np.array_equal(loaded_vectors, vectors)
    assert loaded_manifest.corpus_id == manifest.corpus_id

    store.chunks_path.write_text("tampered\n", encoding="utf-8")
    with pytest.raises(ValueError):
        store.read()
