"""Compact behavioral-coordinate head; it proposes but never authorizes topology."""

from __future__ import annotations

import torch
from torch import nn

from .topology import SIGNATURE_WIDTH


class BehavioralCompiler(nn.Module):
    def __init__(self, hidden: int = 384) -> None:
        super().__init__()
        self.signature = nn.Sequential(nn.Linear(hidden * 4, 384), nn.GELU(), nn.Linear(384, SIGNATURE_WIDTH))
        self.disposition = nn.Linear(hidden, 3)
        self.scope = nn.Linear(hidden, 2)
        self.modality = nn.Linear(hidden, 2)
        self.port = nn.Sequential(nn.Linear(hidden * 5, 256), nn.GELU(), nn.Linear(256, 1))
        self.start = nn.Linear(hidden, 1)
        self.end = nn.Linear(hidden, 1)
        self.kind = nn.Linear(hidden, 3)  # claim, value, event

    @staticmethod
    def pool(tokens: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        return (tokens * mask.unsqueeze(-1)).sum(1) / mask.sum(1, keepdim=True).clamp_min(1)

    @staticmethod
    def span_pool(tokens: torch.Tensor, spans: torch.Tensor) -> torch.Tensor:
        return torch.einsum("bat,bth->bah", spans.float(), tokens) / spans.sum(-1, keepdim=True).clamp_min(1)

    def forward(self, tokens: torch.Tensor, mask: torch.Tensor, spans: torch.Tensor) -> dict[str, torch.Tensor]:
        pooled = self.pool(tokens, mask)
        span = self.span_pool(tokens, spans)
        left, right = span[:, 0], span[:, 1]
        # The behavior cell is invariant to atom presentation order; ports are not.
        behavior_input = torch.cat((pooled, (left + right) / 2, (left - right).abs(), left * right), -1)

        def score(source: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
            return self.port(torch.cat((pooled, source, target, source - target, source * target), -1)).squeeze(-1)

        return {
            "signature": self.signature(behavior_input),
            "disposition": self.disposition(pooled),
            "scope": self.scope(pooled),
            "modality": self.modality(pooled),
            "ports": torch.stack((score(left, right), score(right, left)), -1),
            "start": self.start(tokens).squeeze(-1),
            "end": self.end(tokens).squeeze(-1),
            "kind": self.kind(tokens),
        }
