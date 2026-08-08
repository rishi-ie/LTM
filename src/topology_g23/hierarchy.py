from __future__ import annotations

import torch
from torch import Tensor, nn

from .registry import RELATION_LABELS


class HierarchicalReconciler(nn.Module):
    def __init__(self, state_dim: int = 128, cycles: int = 4, recurrent: bool = True) -> None:
        super().__init__(); self.state_dim = state_dim; self.cycles = cycles; self.recurrent = recurrent
        self.relation_embedding = nn.Embedding(len(RELATION_LABELS), state_dim)
        self.role_embedding = nn.Embedding(64, state_dim)
        self.relation_gru = nn.GRUCell(state_dim, state_dim)
        self.span_gru = nn.GRUCell(state_dim, state_dim)
        self.hub_gru = nn.GRUCell(state_dim, state_dim)
        self.message = nn.Linear(state_dim, state_dim)
        self.scorer = nn.Sequential(nn.Linear(state_dim * 3, state_dim), nn.GELU(), nn.Linear(state_dim, 1))
        self.scope_head = nn.Linear(state_dim, 5)
        self.disposition_head = nn.Linear(state_dim, 3)

    def reconcile(self, span_states: Tensor, hub: Tensor, relation_ids: Tensor, role_ids: Tensor, bound_ids: Tensor) -> tuple[Tensor, Tensor]:
        if relation_ids.numel() == 0:
            return relation_ids.new_empty((0,), dtype=torch.float32), hub
        spans = span_states[0]; relation = self.relation_embedding(relation_ids); hub_state = hub
        for _ in range(self.cycles if self.recurrent else 0):
            bound = spans[bound_ids.clamp_min(0)]
            valid = (bound_ids >= 0).unsqueeze(-1)
            aggregate = (bound * valid).sum(1) / valid.sum(1).clamp_min(1)
            role = self.role_embedding(role_ids.clamp_min(0)).mean(1)
            relation = self.relation_gru(aggregate + role + hub_state.expand_as(aggregate), relation)
            messages = self.message(relation)
            updated = spans.clone()
            for row in range(bound_ids.shape[0]):
                for col in range(bound_ids.shape[1]):
                    index = int(bound_ids[row, col])
                    if index >= 0:
                        updated[index] = self.span_gru(messages[row:row + 1], spans[index:index + 1])[0]
            spans = updated; hub_state = self.hub_gru((relation + aggregate).mean(0, keepdim=True), hub_state)
        bound = spans[bound_ids.clamp_min(0)]; valid = (bound_ids >= 0).unsqueeze(-1)
        aggregate = (bound * valid).sum(1) / valid.sum(1).clamp_min(1)
        scores = self.scorer(torch.cat((relation, aggregate, hub_state.expand_as(relation)), -1)).squeeze(-1)
        return scores, hub_state
