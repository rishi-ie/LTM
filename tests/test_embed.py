"""Embedding boundary checks without loading model weights."""

import numpy as np

from ltm_poc.embed import embed_chunks
from ltm_poc.schemas import ChunkRecord


class FakeEmbedder:
    def encode(self, texts, **_kwargs):
        vector = np.zeros((len(texts), 384), dtype=np.float32)
        vector[:, 0] = 1
        return vector


def test_embedder_returns_normalized_float32_vectors() -> None:
    chunk = ChunkRecord(
        chunk_id="c",
        record_id="r",
        source_path="s",
        source_kind="text",
        text="text",
        char_start=0,
        char_end=4,
        token_start=0,
        token_end=1,
        token_count=1,
        content_hash="hash",
        metadata={},
    )
    vectors = embed_chunks([chunk], FakeEmbedder(), batch_size=1)
    assert vectors.dtype == np.float32
    assert vectors.shape == (1, 384)
