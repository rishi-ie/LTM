from __future__ import annotations

import os

import numpy as np

from .indexes import FactorIndexes
from .schemas import ActiveFrontier, TraversalRequest
from .traverse import build_frontier


def run_controls(request: TraversalRequest, indexes: FactorIndexes):
    modes = ("full", "forward_only", "untyped_bfs", "no_safety", "no_session", "no_correction", "no_conflict")
    return {mode: build_frontier(request, indexes, mode) for mode in modes}


def semantic_topk(requests: list[TraversalRequest], indexes: FactorIndexes, limit: int = 512) -> list[ActiveFrontier]:
    """Frozen MiniLM nearest-factor control; it has no typed traversal authority."""
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    from sentence_transformers import SentenceTransformer

    from topology_g21.encode import MODEL

    factor_ids = tuple(indexes.factors)
    model = SentenceTransformer(str(MODEL), local_files_only=True, device="cpu")
    query_vectors = model.encode([request.target_literal for request in requests], batch_size=128, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False).astype(np.float32)
    best_scores = np.full((len(requests), limit), -np.inf, dtype=np.float32)
    best_positions = np.full((len(requests), limit), -1, dtype=np.int32)
    batch_size = 2048
    for start in range(0, len(factor_ids), batch_size):
        batch_ids = factor_ids[start:start+batch_size]
        descriptions = [" ".join((indexes.factors[fid].factor_type, *indexes.factors[fid].source_ids, *indexes.factors[fid].target_ids)) for fid in batch_ids]
        vectors = model.encode(descriptions, batch_size=256, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False).astype(np.float32)
        scores = query_vectors @ vectors.T
        positions = np.broadcast_to(np.arange(start, start + len(batch_ids), dtype=np.int32), scores.shape)
        combined_scores = np.concatenate((best_scores, scores), axis=1)
        combined_positions = np.concatenate((best_positions, positions), axis=1)
        selected = np.argpartition(combined_scores, -limit, axis=1)[:, -limit:]
        best_scores = np.take_along_axis(combined_scores, selected, axis=1)
        best_positions = np.take_along_axis(combined_positions, selected, axis=1)
    output = []
    for row, request in enumerate(requests):
        selected = tuple(sorted(factor_ids[int(position)] for position in best_positions[row] if position >= 0)); blocks = tuple(sorted({indexes.block(fid) for fid in selected}))
        output.append(ActiveFrontier(request.request_id, request.starting_entity_ids + request.starting_predicate_ids, selected, (), (), tuple(fid for fid in selected if indexes.factors[fid].hard and not indexes.factors[fid].exact_exception), tuple(fid for fid in selected if indexes.factors[fid].exact_exception), tuple(fid for fid in selected if indexes.factors[fid].factor_type in ("excludes", "opposes")), tuple(fid for fid in selected if indexes.factors[fid].session_factor), tuple(fid for fid in selected if indexes.factors[fid].factor_type == "bridge"), (), (), blocks, len(blocks)*indexes.block_size*128, limit, 0, False, 0))
    return output
