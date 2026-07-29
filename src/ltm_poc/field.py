"""Explicit query-weighted directional latent dynamic field."""

from dataclasses import dataclass

import numpy as np

from ltm_poc.config import WorkspaceConfig
from ltm_poc.retrieve import retrieve
from ltm_poc.schemas import ChunkRecord, EvidenceItem


def _logsumexp(values: np.ndarray) -> float:
    maximum = float(np.max(values))
    return maximum + float(np.log(np.exp(values - maximum).sum()))


@dataclass(frozen=True)
class LatentField:
    query: np.ndarray
    vectors: np.ndarray
    evidence: list[EvidenceItem]
    log_weights: np.ndarray
    query_temperature: float
    field_temperature: float
    query_anchor: float

    @classmethod
    def construct(
        cls,
        query: np.ndarray,
        corpus_vectors: np.ndarray,
        chunks: list[ChunkRecord],
        config: WorkspaceConfig,
    ) -> "LatentField":
        indices, evidence = retrieve(
            query, corpus_vectors, chunks, config.active_candidates
        )
        vectors = corpus_vectors[indices].astype(np.float64)
        q = query.astype(np.float64)
        scores = vectors @ q / config.query_temperature
        return cls(
            query=q,
            vectors=vectors,
            evidence=evidence,
            log_weights=scores - _logsumexp(scores),
            query_temperature=config.query_temperature,
            field_temperature=config.field_temperature,
            query_anchor=config.query_anchor,
        )

    def energy_and_gradient(self, state: np.ndarray) -> tuple[float, np.ndarray]:
        if state.shape != (384,) or not np.isclose(
            np.linalg.norm(state), 1.0, atol=1e-6
        ):
            raise ValueError("field state must be a unit 384-vector")
        logits = self.log_weights + (self.vectors @ state) / self.field_temperature
        log_partition = _logsumexp(logits)
        weights = np.exp(logits - log_partition)
        energy = -log_partition + self.query_anchor * (1.0 - float(state @ self.query))
        gradient = (
            -(weights @ self.vectors) / self.field_temperature
            - self.query_anchor * self.query
        )
        return float(energy), gradient
