"""Batch embedding with the frozen semantic model."""

from typing import Any, Iterable

import numpy as np

from ltm_poc.schemas import ChunkRecord


def embed_chunks(
    chunks: Iterable[ChunkRecord], model: Any, batch_size: int
) -> np.ndarray:
    chunk_list = list(chunks)
    if not chunk_list:
        return np.empty((0, 384), dtype=np.float32)
    vectors = np.asarray(
        model.encode(
            [chunk.text for chunk in chunk_list],
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            precision="float32",
            show_progress_bar=False,
        ),
        dtype=np.float32,
    )
    if vectors.shape != (len(chunk_list), 384):
        raise ValueError(
            f"expected {len(chunk_list)} vectors of dimension 384, got {vectors.shape}"
        )
    if not np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-4):
        raise ValueError("embedding model did not return normalized vectors")
    return vectors
