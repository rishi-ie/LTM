"""Deterministic traditional-RAG baselines for Phase 1.3.

The implementation intentionally has no extra retrieval dependency.  BM25 is
small enough to keep here, and keeping tokenisation and tie breaking explicit
makes comparisons reproducible across machines.
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np

from ltm_poc.schemas import ChunkRecord, EvidenceItem

_TOKEN = re.compile(r"(?u)\b\w+\b")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.casefold())


@dataclass(frozen=True)
class BM25Index:
    """A frozen Okapi BM25 index with deterministic postings."""

    postings: dict[str, tuple[tuple[int, int], ...]]
    idf: dict[str, float]
    lengths: tuple[int, ...]
    average_length: float
    k1: float = 1.2
    b: float = 0.75

    @classmethod
    def build(
        cls, chunks: Sequence[ChunkRecord], k1: float = 1.2, b: float = 0.75
    ) -> "BM25Index":
        if k1 <= 0 or not 0 <= b <= 1:
            raise ValueError("BM25 requires k1 > 0 and b in [0, 1]")
        postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        lengths: list[int] = []
        for index, chunk in enumerate(chunks):
            counts = Counter(tokenize(chunk.text))
            lengths.append(sum(counts.values()))
            for token, frequency in counts.items():
                postings[token].append((index, frequency))
        document_count = len(chunks)
        idf = {
            token: math.log1p((document_count - len(rows) + 0.5) / (len(rows) + 0.5))
            for token, rows in postings.items()
        }
        return cls(
            postings={token: tuple(rows) for token, rows in postings.items()},
            idf=idf,
            lengths=tuple(lengths),
            average_length=(sum(lengths) / document_count if document_count else 1.0),
            k1=k1,
            b=b,
        )

    def scores(self, query: str) -> np.ndarray:
        scores = np.zeros(len(self.lengths), dtype=np.float64)
        query_terms = Counter(tokenize(query))
        for token, query_frequency in query_terms.items():
            rows = self.postings.get(token)
            if not rows:
                continue
            weight = self.idf[token] * (1.0 + math.log1p(query_frequency))
            for index, frequency in rows:
                denominator = frequency + self.k1 * (
                    1.0
                    - self.b
                    + self.b * self.lengths[index] / max(self.average_length, 1e-12)
                )
                scores[index] += weight * frequency * (self.k1 + 1.0) / denominator
        return scores

    def rank(self, query: str, chunks: Sequence[ChunkRecord], limit: int) -> list[int]:
        if len(chunks) != len(self.lengths) or limit <= 0:
            raise ValueError("invalid BM25 corpus or limit")
        scores = self.scores(query)
        return sorted(
            range(len(chunks)),
            key=lambda index: (-float(scores[index]), chunks[index].chunk_id),
        )[:limit]


def evidence_for_indices(
    indices: Iterable[int],
    chunks: Sequence[ChunkRecord],
    scores: Sequence[float] | None = None,
) -> list[EvidenceItem]:
    values = scores if scores is not None else [0.0] * len(chunks)
    return [
        EvidenceItem(
            rank=rank,
            chunk_id=chunks[index].chunk_id,
            source_path=chunks[index].source_path,
            score=float(values[index]),
            text=chunks[index].text,
        )
        for rank, index in enumerate(indices, start=1)
    ]


def bm25_retrieve(
    query: str, chunks: Sequence[ChunkRecord], index: BM25Index, limit: int
) -> list[EvidenceItem]:
    scores = index.scores(query)
    return evidence_for_indices(index.rank(query, chunks, limit), chunks, scores)


def rrf_indices(
    rankings: Sequence[Sequence[int]],
    chunks: Sequence[ChunkRecord],
    limit: int,
    k: int = 60,
) -> list[int]:
    """Merge rankings with reciprocal-rank fusion and stable ID ties."""
    if k <= 0 or limit <= 0:
        raise ValueError("invalid RRF parameters")
    scores: defaultdict[int, float] = defaultdict(float)
    for ranking in rankings:
        for rank, index in enumerate(ranking, start=1):
            scores[index] += 1.0 / (k + rank)
    return sorted(
        scores,
        key=lambda index: (-scores[index], chunks[index].chunk_id),
    )[:limit]


def hybrid_retrieve(
    query: str,
    query_vector: np.ndarray,
    vectors: np.ndarray,
    chunks: Sequence[ChunkRecord],
    index: BM25Index,
    limit: int = 4,
    pool: int = 100,
    rrf_k: int = 60,
) -> list[EvidenceItem]:
    dense_scores = vectors @ query_vector.astype(np.float32)
    dense = sorted(
        range(len(chunks)),
        key=lambda item: (-float(dense_scores[item]), chunks[item].chunk_id),
    )[:pool]
    lexical = index.rank(query, chunks, min(pool, len(chunks)))
    fused = rrf_indices((lexical, dense), chunks, limit, rrf_k)
    return evidence_for_indices(fused, chunks, dense_scores)


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[int]], chunks: Sequence[ChunkRecord], limit: int = 4
) -> list[EvidenceItem]:
    return evidence_for_indices(rrf_indices(rankings, chunks, limit), chunks)
