"""Small coordinate heads; no direct relation prediction path."""

from __future__ import annotations

import torch
from torch import nn


class AtomicMeasurementHead(nn.Module):
    def __init__(self, feature_count: int, hidden: int = 384) -> None:
        super().__init__()
        self.unary = nn.Sequential(nn.Linear(hidden, 192), nn.GELU(), nn.Linear(192, feature_count))
        self.pair = nn.Sequential(nn.Linear(hidden * 4, 256), nn.GELU(), nn.Linear(256, feature_count))
        self.context = nn.Sequential(nn.Linear(hidden, 128), nn.GELU(), nn.Linear(128, feature_count))

    def forward(self, token_states: torch.Tensor, spans: torch.Tensor) -> dict[str, torch.Tensor]:
        span_states = torch.einsum("bst,bth->bsh", spans.float(), token_states)
        span_states = span_states / spans.sum(-1, keepdim=True).clamp_min(1.0)
        unary = self.unary(span_states)
        left = span_states.unsqueeze(2)
        right = span_states.unsqueeze(1)
        left_expanded = left.expand(-1, -1, right.shape[2], -1)
        right_expanded = right.expand(-1, left.shape[1], -1, -1)
        pair_input = torch.cat((left_expanded, right_expanded, left_expanded - right_expanded, left_expanded * right_expanded), -1)
        pair = self.pair(pair_input)
        context = self.context(token_states.mean(1))
        return {"unary": unary, "pair": pair, "context": context}
