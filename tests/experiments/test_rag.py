"""First-principles checks for the Phase 1.3 retrieval controls."""

import numpy as np

from ltm_poc.experiments.common import chunks_from_documents
from ltm_poc.experiments.rag import BM25Index, hybrid_retrieve, rrf_indices, tokenize


def test_bm25_is_casefolded_and_stably_tied() -> None:
    chunks = chunks_from_documents({"b": "Alpha", "a": "alpha", "c": "beta"})
    index = BM25Index.build(chunks)
    assert tokenize("Alpha's TEST") == ["alpha", "s", "test"]
    assert index.rank("alpha", chunks, 2) == [1, 0]


def test_rrf_uses_rank_not_raw_scores_and_id_ties() -> None:
    chunks = chunks_from_documents({"b": "b", "a": "a", "c": "c"})
    assert rrf_indices(([1, 0], [0, 1]), chunks, 3)[:2] == [1, 0]


def test_hybrid_returns_bounded_unique_evidence() -> None:
    chunks = chunks_from_documents({"a": "alpha fact", "b": "beta fact"})
    vectors = np.eye(384, dtype=np.float32)[:2]
    query = vectors[0]
    evidence = hybrid_retrieve(
        "alpha", query, vectors, chunks, BM25Index.build(chunks), 2
    )
    assert [item.chunk_id for item in evidence] == ["a", "b"]
