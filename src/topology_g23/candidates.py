from __future__ import annotations

import hashlib

import torch

from .registry import RELATION_LABELS, enumerate_legal_candidates
from .schemas import RelationHypothesis, TypedSpanCandidate


def candidate_tensors(spans: tuple[TypedSpanCandidate, ...], maximum: int = 96):
    legal = enumerate_legal_candidates(spans, maximum)
    indices = {span.candidate_id: index for index, span in enumerate(spans)}
    relation_ids: list[int] = []; role_ids: list[list[int]] = []; bound_ids: list[list[int]] = []
    role_names: list[str] = []
    for relation, bindings, _score in legal:
        relation_ids.append(RELATION_LABELS.index(relation)); role_row = []; bound_row = []
        for role, local_ids in bindings:
            if role not in role_names: role_names.append(role)
            role_row.append(int(hashlib.sha256(role.encode()).hexdigest()[:8], 16) % 63)
            bound_row.extend(indices[item] for item in local_ids)
        role_ids.append((role_row + [0, 0, 0])[:3]); bound_ids.append((bound_row + [-1, -1, -1, -1])[:4])
    if not legal:
        return (torch.empty(0, dtype=torch.long), torch.empty((0, 3), dtype=torch.long), torch.empty((0, 4), dtype=torch.long), ()), legal
    return (torch.tensor(relation_ids), torch.tensor(role_ids), torch.tensor(bound_ids), tuple(role_names)), legal


def relation_hypotheses(spans: tuple[TypedSpanCandidate, ...], scores: torch.Tensor, legal, scope_id: str = "global") -> tuple[RelationHypothesis, ...]:
    if not legal: return ()
    # Each legal graph is an independent candidate: a sentence can contain
    # multiple compatible relations, so probabilities must not compete in one
    # softmax bucket.
    probabilities = torch.sigmoid(scores).tolist()
    ordered = sorted(range(len(legal)), key=lambda index: (-probabilities[index], legal[index][0], legal[index][1]))
    out = []
    for index in ordered[:8]:
        relation, bindings, _ = legal[index]
        out.append(RelationHypothesis(f"h-{index}", relation, bindings, scope_id, None, None, float(probabilities[index])))
    return tuple(out)
