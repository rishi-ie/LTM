"""One shared coordinate transform and certified terminal-completion dynamics."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from .field import AlignedField
from .schemas import DynamicPrompt, InferenceResult, TraceStep


class AlignedTransitionKernel(nn.Module):
    def __init__(self, input_dimension: int = 384, state_dimension: int = 128) -> None:
        super().__init__()
        self.encoder = nn.Sequential(nn.Linear(input_dimension, state_dimension), nn.Tanh(), nn.Linear(state_dimension, state_dimension))

    def project(self, values: torch.Tensor) -> torch.Tensor:
        return F.normalize(self.encoder(values), dim=-1, eps=1e-6)


def parameter_count(model: nn.Module) -> int:
    return sum(value.numel() for value in model.parameters())


def train_kernel(field: AlignedField, steps: int, batch_size: int, seed: int) -> tuple[AlignedTransitionKernel, list[float]]:
    """Learn an aligned state space from bodies; phase gives observations, not relations."""
    torch.manual_seed(seed)
    torch.set_num_threads(4)
    model = AlignedTransitionKernel(field.vectors.shape[1])
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=.01)
    rng = np.random.default_rng(seed)
    body_ids = tuple(sorted(field.bodies))
    raw_source = np.asarray([field.vectors[field.body_source_units[item].semantic_vector_ref] for item in body_ids], dtype=np.float32)
    raw_outcome = np.asarray([field.vectors[field.body_outcome_units[item].semantic_vector_ref] for item in body_ids], dtype=np.float32)
    losses: list[float] = []
    model.train()
    for _ in range(steps):
        selected = rng.choice(len(body_ids), size=min(batch_size, len(body_ids)), replace=False)
        source = torch.from_numpy(raw_source[selected])
        outcome = torch.from_numpy(raw_outcome[selected])
        source_state = model.project(source)
        outcome_state = model.project(outcome)
        # The predicted next state uses an observed, unnamed body displacement.
        prediction = F.normalize(source_state + (outcome_state - source_state), dim=-1, eps=1e-6)
        labels = torch.arange(len(selected))
        temperature = 12.0
        source_loss = F.cross_entropy(temperature * source_state @ source_state.T, labels)
        outcome_loss = F.cross_entropy(temperature * prediction @ outcome_state.T, labels)
        reverse_loss = F.relu(.25 - (prediction * outcome_state).sum(-1) + (source_state * outcome_state).sum(-1)).mean()
        loss = source_loss + outcome_loss + .25 * reverse_loss
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        losses.append(float(loss.detach()))
    return model.eval(), losses


def save_kernel(path: Path, model: AlignedTransitionKernel, losses: list[float], seed: int) -> dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model": model.state_dict(), "losses": losses, "seed": seed}, path)
    return {"parameters": parameter_count(model), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "final_loss": losses[-1]}


def load_kernel(path: Path) -> AlignedTransitionKernel:
    payload = torch.load(path, map_location="cpu", weights_only=False)
    model = AlignedTransitionKernel()
    model.load_state_dict(payload["model"])
    return model.eval()


def _hash(value: np.ndarray) -> str:
    return hashlib.sha256(value.astype(np.float32).tobytes()).hexdigest()


def infer(model: AlignedTransitionKernel, field: AlignedField, prompt: DynamicPrompt, *, confidence: float = .95) -> InferenceResult:
    if not field.source_state:
        raise RuntimeError("aligned field must be refreshed before inference")
    anchor, entity = field.prompt_state(prompt.clamped_unit_ids, model)
    state = anchor.copy()
    current_identity = field.units[prompt.clamped_unit_ids[0]].identity_key
    trace: list[TraceStep] = []
    visited: list[str] = []
    last_candidate: str | None = None
    last_energy = float("inf")
    for step in range(prompt.maximum_steps):
        frontier = field.frontier(state, entity, prompt.scope_key, prompt.maximum_bodies, current_identity)
        if not frontier:
            break
        ranked = sorted(frontier, key=lambda body_id: (-float(np.dot(state, field.source_state[body_id])), body_id))
        body_id = ranked[0]
        source_score = float(np.dot(state, field.source_state[body_id]))
        if source_score < confidence:
            break
        proposed = field._normalize(state + (field.outcome_state[body_id] - field.source_state[body_id]))
        energy = max(0.0, 1.0 - float(np.dot(proposed, field.outcome_state[body_id])))
        if energy < 1e-5:
            energy = 0.0
        accepted = energy <= last_energy + 1e-5
        if not accepted:
            trace.append(TraceStep(step, energy, False, body_id, _hash(state)))
            break
        state = proposed
        last_energy = energy
        visited.append(body_id)
        last_candidate = field.body_outcome_units[body_id].unit_id
        current_identity = field.body_outcome_units[body_id].identity_key
        entity = current_identity.split("|", 1)[0]
        trace.append(TraceStep(step, energy, True, body_id, _hash(state)))
    final_frontier = field.frontier(state, entity, prompt.scope_key, prompt.maximum_bodies, current_identity)
    terminal = bool(last_candidate) and (not final_frontier or max(float(np.dot(state, field.source_state[item])) for item in final_frontier) < confidence)
    if terminal:
        return InferenceResult(prompt.prompt_id, "candidate", last_candidate, ((last_candidate, 1.0),), tuple(visited), tuple(trace), "certified")
    if not visited:
        return InferenceResult(prompt.prompt_id, "unknown", None, (), (), tuple(trace), "certified")
    return InferenceResult(prompt.prompt_id, "incomplete_frontier", None, ((last_candidate, 1.0),) if last_candidate else (), tuple(visited), tuple(trace), "incomplete_frontier")
