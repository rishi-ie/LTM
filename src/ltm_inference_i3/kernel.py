"""Compact learned proposal scorer for I3 proof search."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.nn import functional as f

from .dataset import expr_from_obj, expression_feature, load_jsonl, proposition_from_obj
from .formal import standard_axioms


class ProofKernel(nn.Module):
    def __init__(self, axiom_count: int = 46, dimension: int = 128) -> None:
        super().__init__()
        self.state = nn.Sequential(nn.Linear(384, dimension), nn.Tanh(), nn.Linear(dimension, dimension))
        self.goal = nn.Sequential(nn.Linear(384, dimension), nn.Tanh(), nn.Linear(dimension, dimension))
        self.axioms = nn.Parameter(torch.empty(axiom_count, dimension))
        self.energy = nn.Sequential(nn.Linear(dimension * 2, dimension), nn.Tanh(), nn.Linear(dimension, 1))
        nn.init.normal_(self.axioms, std=.02)

    def logits(self, state: torch.Tensor, goal: torch.Tensor) -> torch.Tensor:
        state_code = f.normalize(self.state(state), dim=-1)
        goal_code = f.normalize(self.goal(goal), dim=-1)
        query = f.normalize(state_code + goal_code, dim=-1)
        return 12.0 * query @ f.normalize(self.axioms, dim=-1).T

    def potential(self, state: torch.Tensor, goal: torch.Tensor) -> torch.Tensor:
        return self.energy(torch.cat((self.state(state), self.goal(goal)), dim=-1)).squeeze(-1)


def parameter_count(model: nn.Module) -> int:
    return sum(value.numel() for value in model.parameters())


def _examples(workspace: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    public = {str(row["problem_id"]): row for row in load_jsonl(workspace / "public" / "train" / "theorems.jsonl")}
    gold = load_jsonl(workspace / "evaluator-gold" / "train" / "gold.jsonl")
    index = {item.axiom_id: position for position, item in enumerate(standard_axioms())}
    states: list[np.ndarray] = []
    goals: list[np.ndarray] = []
    labels: list[int] = []
    next_states: list[np.ndarray] = []
    for row in gold:
        if row["status"] != "proved":
            continue
        problem = public[str(row["problem_id"])]
        goal = proposition_from_obj(problem["goal"]).right
        for step in row["proof"]:
            states.append(expression_feature(expr_from_obj(step["before"])))
            next_states.append(expression_feature(expr_from_obj(step["after"])))
            goals.append(expression_feature(goal))
            labels.append(index[str(step["axiom_id"])])
    return (
        np.asarray(states, dtype=np.float32),
        np.asarray(next_states, dtype=np.float32),
        np.asarray(goals, dtype=np.float32),
        np.asarray(labels, dtype=np.int64),
    )


def train_kernel(workspace: Path, steps: int, batch_size: int, seed: int, learning_rate: float) -> tuple[ProofKernel, list[float]]:
    torch.manual_seed(seed)
    torch.set_num_threads(4)
    states, next_states, goals, labels = _examples(workspace)
    model = ProofKernel()
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=.01)
    rng = np.random.default_rng(seed)
    losses: list[float] = []
    for _ in range(steps):
        selected = rng.choice(len(labels), size=min(batch_size, len(labels)), replace=False)
        state = torch.from_numpy(states[selected])
        next_state = torch.from_numpy(next_states[selected])
        goal = torch.from_numpy(goals[selected])
        target = torch.from_numpy(labels[selected])
        logits = model.logits(state, goal)
        classification = f.cross_entropy(logits, target)
        before_energy = model.potential(state, goal)
        after_energy = model.potential(next_state, goal)
        trajectory = f.relu(.2 + after_energy - before_energy).mean()
        negative_energy = model.potential(torch.roll(next_state, 1, 0), goal)
        contrast = f.relu(.1 + after_energy - negative_energy).mean()
        loss = classification + .50 * trajectory + .20 * contrast
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        losses.append(float(loss.detach()))
    return model.eval(), losses


def save_kernel(path: Path, model: ProofKernel, losses: list[float], seed: int) -> dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model": model.state_dict(), "losses": losses, "seed": seed}, path)
    return {"parameters": parameter_count(model), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "final_loss": losses[-1]}


def load_kernel(path: Path) -> ProofKernel:
    payload = torch.load(path, map_location="cpu", weights_only=False)
    model = ProofKernel()
    model.load_state_dict(payload["model"])
    return model.eval()
