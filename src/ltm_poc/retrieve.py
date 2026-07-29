"""Exact deterministic cosine retrieval over normalized vectors."""

import numpy as np

from ltm_poc.schemas import ChunkRecord, EvidenceItem


def retrieve(
    query: np.ndarray, vectors: np.ndarray, chunks: list[ChunkRecord], limit: int
) -> tuple[np.ndarray, list[EvidenceItem]]:
    if vectors.shape != (len(chunks), 384) or limit <= 0:
        raise ValueError("invalid corpus vectors or retrieval limit")
    if not np.isclose(np.linalg.norm(query), 1.0, atol=1e-4):
        raise ValueError("query vector must be unit normalized")
    if not np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-4):
        raise ValueError("corpus vectors must be unit normalized")
    scores = vectors @ query.astype(np.float32)

    def sort_key(index: int) -> tuple[float, str]:
        return -float(scores[index]), chunks[index].chunk_id

    ordered = sorted(range(len(chunks)), key=sort_key)
    indices = np.asarray(ordered[:limit], dtype=np.int64)
    evidence = [
        EvidenceItem(
            rank=rank,
            chunk_id=chunks[index].chunk_id,
            source_path=chunks[index].source_path,
            score=float(scores[index]),
            text=chunks[index].text,
        )
        for rank, index in enumerate(indices, start=1)
    ]
    return indices, evidence
