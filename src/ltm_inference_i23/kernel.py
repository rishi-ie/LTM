"""Shared learned projection, summary encoder and explicit local field energy."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.nn import functional

from .field import PublicField


class FieldKernel(nn.Module):
    def __init__(self, input_dimension: int = 384, state_dimension: int = 128) -> None:
        super().__init__()
        self.projector = nn.Sequential(nn.Linear(input_dimension, state_dimension), nn.Tanh(), nn.Linear(state_dimension, state_dimension))

    def project(self, value: torch.Tensor) -> torch.Tensor:
        return functional.normalize(self.projector(value), dim=-1, eps=1e-6)

def parameter_count(model: nn.Module) -> int:
    return sum(value.numel() for value in model.parameters())


def train_kernel(field: PublicField, steps: int, batch_size: int, seed: int, learning_rate: float) -> tuple[FieldKernel, list[float]]:
    torch.manual_seed(seed)
    torch.set_num_threads(4)
    model = FieldKernel(field.vectors.shape[1])
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=.01)
    rng = np.random.default_rng(seed)
    body_ids = tuple(sorted(field.bodies))
    source = np.asarray([field.vectors[field.source_units[item].semantic_vector_ref] for item in body_ids], dtype=np.float32)
    outcome = np.asarray([field.vectors[field.outcome_units[item].semantic_vector_ref] for item in body_ids], dtype=np.float32)
    losses: list[float] = []
    for _ in range(steps):
        selected = rng.choice(len(body_ids), size=min(batch_size, len(body_ids)), replace=False)
        source_value = torch.from_numpy(source[selected])
        outcome_value = torch.from_numpy(outcome[selected])
        source_state = model.project(source_value)
        outcome_state = model.project(outcome_value)
        labels = torch.arange(len(selected))
        contrastive = functional.cross_entropy(16.0 * source_state @ source_state.T, labels)
        # An observed outcome is positive; a reversed endpoint is a hard negative.
        margin = functional.relu(.20 - (outcome_state * source_state).sum(dim=-1) + (outcome_state * torch.roll(source_state, 1, 0)).sum(dim=-1)).mean()
        loss = contrastive + .25 * margin
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        losses.append(float(loss.detach()))
    return model.eval(), losses


def save_kernel(path: Path, model: FieldKernel, losses: list[float], seed: int) -> dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model": model.state_dict(), "losses": losses, "seed": seed}, path)
    return {"parameters": parameter_count(model), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "final_loss": losses[-1]}


def load_kernel(path: Path) -> FieldKernel:
    payload = torch.load(path, map_location="cpu", weights_only=False)
    model = FieldKernel()
    model.load_state_dict(payload["model"])
    return model.eval()
