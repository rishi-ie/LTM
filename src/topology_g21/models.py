from __future__ import annotations

import torch
from torch import nn


class MultiHead(nn.Module):
    def __init__(self, input_dimension: int, role_count: int, nonlinear: bool) -> None:
        super().__init__()
        self.nonlinear = nonlinear
        if nonlinear:
            self.body = nn.Sequential(nn.Linear(input_dimension, 256), nn.GELU(), nn.LayerNorm(256), nn.Dropout(0.10), nn.Linear(256, 128))
            dimension = 128
        else:
            self.body = nn.Identity()
            dimension = input_dimension
        self.relation = nn.Linear(dimension, 20)
        self.direction = nn.Linear(dimension, 5)
        self.roles = nn.ModuleList([nn.Linear(dimension, role_count) for _ in range(3)])
        self.scope = nn.Linear(dimension, 5)
        self.disposition = nn.Linear(dimension, 3)

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        hidden = self.body(x)
        embedding = torch.nn.functional.normalize(hidden, dim=-1) if self.nonlinear else hidden
        return {"relation": self.relation(hidden), "direction": self.direction(hidden), "roles": torch.stack([head(hidden) for head in self.roles], dim=1), "scope": self.scope(hidden), "disposition": self.disposition(hidden), "embedding": embedding}
