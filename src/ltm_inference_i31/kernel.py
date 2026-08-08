"""Goal-conditioned body scoring and remaining-proof-cost estimate."""

from __future__ import annotations

import numpy as np
import torch
from torch import nn
from torch.nn import functional as f


class SearchKernel(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.score = nn.Sequential(nn.Linear(512, 192), nn.Tanh(), nn.Linear(192, 1))
        self.remaining = nn.Sequential(nn.Linear(256, 128), nn.Tanh(), nn.Linear(128, 1))

    def body_score(self, state: torch.Tensor, goal: torch.Tensor, body: torch.Tensor) -> torch.Tensor:
        left, right = body[:, :128], body[:, 128:]
        structural = .75 * (f.normalize(state, dim=-1) * f.normalize(left, dim=-1)).sum(dim=-1)
        goal_alignment = .75 * (f.normalize(goal, dim=-1) * f.normalize(right, dim=-1)).sum(dim=-1)
        return self.score(torch.cat((state, goal, body), dim=-1)).squeeze(-1) + structural + goal_alignment

    def remaining_cost(self, state: torch.Tensor, goal: torch.Tensor) -> torch.Tensor:
        return self.remaining(torch.cat((state, goal), dim=-1)).squeeze(-1)


def parameter_count(model: nn.Module) -> int:
    return sum(item.numel() for item in model.parameters())


def train_kernel(examples: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray], *, steps: int, seed: int) -> SearchKernel:
    states, goals, positives, negatives, distances = examples
    torch.manual_seed(seed); torch.set_num_threads(4)
    model = SearchKernel(); optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=.01)
    rng = np.random.default_rng(seed)
    for _ in range(steps):
        rows = rng.choice(len(states), size=min(64, len(states)), replace=False)
        state = torch.from_numpy(states[rows]); goal = torch.from_numpy(goals[rows])
        pos = torch.from_numpy(positives[rows]); neg = torch.from_numpy(negatives[rows])
        distance = torch.from_numpy(distances[rows])
        ranking = f.relu(.5 - model.body_score(state, goal, pos) + model.body_score(state, goal, neg)).mean()
        value = f.mse_loss(model.remaining_cost(state, goal), distance)
        loss = ranking + .2 * value
        optimizer.zero_grad(set_to_none=True); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); optimizer.step()
    return model.eval()
