"""Learned transition gates and multiscale movable-state inference."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import torch
from torch import nn

from .index import FieldIndex
from .schemas import (
    DynamicInferencePrompt,
    DynamicInferenceResult,
    DynamicOptimizationStep,
    FrontierSnapshot,
    LatentCandidate,
    LatentFieldState,
)


class TransitionKernel(nn.Module):
    def __init__(self, input_dimension: int = 384, state_dimension: int = 128) -> None:
        super().__init__()
        self.projector = nn.Linear(input_dimension, state_dimension)
        self.gate = nn.Sequential(
            nn.Linear(state_dimension * 3, 64),
            nn.Tanh(),
            nn.Linear(64, 1),
        )

    def project(self, values: torch.Tensor) -> torch.Tensor:
        projected = self.projector(values)
        return projected / projected.norm(dim=-1, keepdim=True).clamp_min(1e-6)

    def compatibility(self, query: torch.Tensor, source: torch.Tensor, outcome: torch.Tensor) -> torch.Tensor:
        return torch.sigmoid(self.gate(torch.cat((query, source, outcome), dim=-1))).squeeze(-1)


def parameter_count(model: nn.Module) -> int:
    return sum(item.numel() for item in model.parameters())


def train_kernel(index: FieldIndex, vectors: np.ndarray, steps: int, seed: int) -> tuple[TransitionKernel, list[float]]:
    torch.manual_seed(seed)
    torch.set_num_threads(4)
    model = TransitionKernel(vectors.shape[1])
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=.01)
    rng = np.random.default_rng(seed)
    bodies = tuple(index.bodies.values())
    losses: list[float] = []
    model.train()
    for _ in range(steps):
        body = bodies[int(rng.integers(len(bodies)))]
        source = np.mean([vectors[item.semantic_vector_ref] for item in index.body_units(body) if item.phase_index == 0], axis=0)
        outcome = np.mean([vectors[item.semantic_vector_ref] for item in index.body_units(body) if item.phase_index == 1], axis=0)
        other = vectors[int(rng.integers(len(vectors)))]
        source_t = torch.from_numpy(source).float().reshape(1, -1)
        outcome_t = torch.from_numpy(outcome).float().reshape(1, -1)
        other_t = torch.from_numpy(other).float().reshape(1, -1)
        source_state = model.project(source_t)
        outcome_state = model.project(outcome_t)
        negative_state = model.project(other_t)
        positive = model.compatibility(source_state, source_state, outcome_state)
        negative = model.compatibility(negative_state, source_state, outcome_state)
        loss = torch.relu(.35 - positive + negative).mean()
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        losses.append(float(loss.detach()))
    return model.eval(), losses


def save_kernel(path: Path, model: TransitionKernel, losses: list[float], seed: int) -> dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"model": model.state_dict(), "losses": losses, "seed": seed, "parameters": parameter_count(model)}
    torch.save(payload, path)
    return {"path": str(path), "parameters": parameter_count(model), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "final_loss": losses[-1] if losses else None}


def load_kernel(path: Path, dimension: int = 384) -> TransitionKernel:
    payload = torch.load(path, map_location="cpu", weights_only=False)
    model = TransitionKernel(dimension)
    model.load_state_dict(payload["model"])
    return model.eval()


def _state_hash(position: np.ndarray, activations: dict[str, float]) -> str:
    return hashlib.sha256(position.astype(np.float32).tobytes() + repr(sorted(activations.items())).encode()).hexdigest()


def _frontier_hash(cells: tuple[object, ...], bodies: tuple[object, ...]) -> str:
    return hashlib.sha256(repr((tuple(cell.cell_id for cell in cells), tuple(body.body_id for body in bodies))).encode()).hexdigest()


def infer(model: TransitionKernel, index: FieldIndex, vectors: np.ndarray, prompt: DynamicInferencePrompt, confidence: float = .70, margin_threshold: float = .05) -> DynamicInferenceResult:
    clamped = np.mean([vectors[index.units[item].semantic_vector_ref] for item in prompt.clamped_unit_ids], axis=0)
    with torch.no_grad():
        q = model.project(torch.from_numpy(clamped).float().reshape(1, -1)).numpy()[0]
    position = q.copy()
    initial = LatentFieldState(tuple(float(v) for v in position), (), (), _state_hash(position, {}))
    activations: dict[str, float] = {}
    supports: dict[str, set[str]] = {}
    frontier_trace: list[FrontierSnapshot] = []
    trace: list[DynamicOptimizationStep] = []
    opened_bodies: dict[str, object] = {}
    previous_frontier: tuple[str, ...] = ()
    converged_count = 0
    last_energy = float("inf")
    for step in range(prompt.maximum_steps):
        cells, bodies = index.frontier(position, prompt.maximum_bodies)
        for body in bodies:
            opened_bodies[body.body_id] = body
        body_ids = tuple(sorted(opened_bodies))
        frontier_hash = _frontier_hash(cells, bodies)
        global_delta = np.zeros(128, dtype=np.float32)
        global_weight = 0.0
        for cell in cells:
            row = cell.transition_basis_refs[0]
            delta = index.summary_vectors[row, 256:384]
            score = max(0.0, float(np.dot(index.summary_vectors[row, :128], position)))
            global_delta += score * delta
            global_weight += score
        if global_weight:
            global_delta /= global_weight
        local_delta = np.zeros(128, dtype=np.float32)
        local_weight = 0.0
        body_arrays = [(body, index.body_input(body.body_id), index.body_output(body.body_id)) for body in bodies]
        with torch.no_grad():
            query_batch = torch.from_numpy(np.repeat(position[None, :], len(body_arrays), axis=0)).float()
            source_batch = torch.from_numpy(np.asarray([item[1] for item in body_arrays], dtype=np.float32))
            outcome_batch = torch.from_numpy(np.asarray([item[2] for item in body_arrays], dtype=np.float32))
            gates = model.compatibility(query_batch, source_batch, outcome_batch).numpy()
        for (body, source, outcome), gate in zip(body_arrays, gates):
            source_score = max(0.0, float(np.dot(position, source)))
            gate = float(gate)
            strength = source_score * gate
            if strength <= .05:
                continue
            delta = outcome - source
            local_delta += strength * delta
            local_weight += strength
            for unit in index.body_units(body):
                if unit.phase_index != 1:
                    continue
                activations[unit.unit_id] = max(activations.get(unit.unit_id, 0.0), strength)
                supports.setdefault(unit.unit_id, set()).add(body.body_id)
        if local_weight:
            local_delta /= local_weight
        direction = .65 * global_delta + .35 * local_delta
        proposed = position + .55 * direction
        proposed /= max(1e-8, float(np.linalg.norm(proposed)))
        energy = float(np.linalg.norm(proposed - (position + direction)) ** 2 + .01 * sum(value * value for value in activations.values()))
        learning_rate = .55
        accepted = energy <= last_energy + 1e-7
        if not accepted:
            proposed = position + .5 * (proposed - position)
            proposed /= max(1e-8, float(np.linalg.norm(proposed)))
            energy = min(last_energy, energy)
            learning_rate = .275
        residual = float(np.linalg.norm(proposed - position))
        position = proposed
        if residual < 1e-3 and tuple(sorted(body_ids)) == previous_frontier:
            converged_count += 1
        else:
            converged_count = 0
        previous_frontier = tuple(sorted(body_ids))
        frontier_trace.append(FrontierSnapshot(step, tuple(cell.cell_id for cell in cells), body_ids, tuple(unit.unit_id for body in bodies for unit in index.body_units(body)), tuple(body_ids), (), min(1.0, len(body_ids) / max(1, prompt.maximum_bodies)), frontier_hash))
        state_hash = _state_hash(position, activations)
        trace.append(DynamicOptimizationStep(step, energy, residual, accepted, learning_rate, state_hash, frontier_hash))
        last_energy = energy
        if converged_count >= 2:
            break
    ranked = sorted(activations.items(), key=lambda item: (-item[1], item[0]))
    candidates: list[LatentCandidate] = []
    for rank, (atom_id, value) in enumerate(ranked[:8]):
        second = ranked[rank + 1][1] if rank + 1 < len(ranked) else 0.0
        unit = index.units[atom_id]
        candidates.append(LatentCandidate(atom_id, float(value), float(value - second), tuple(sorted(supports.get(atom_id, ()))), (unit.provenance_id,)))
    stable = converged_count >= 2
    coverage = "certified" if stable and frontier_trace and frontier_trace[-1].coverage_bound >= .9 else "incomplete_frontier"
    selected = candidates[0].atom_id if candidates and stable and coverage == "certified" and candidates[0].probability >= confidence and candidates[0].margin >= margin_threshold else None
    if not stable:
        disposition = "incomplete_frontier"
    elif not candidates:
        disposition = "unknown"
    elif selected:
        disposition = "candidate"
    else:
        disposition = "ambiguous"
    final = LatentFieldState(tuple(float(v) for v in position), tuple((key, float(value)) for key, value in ranked[:64]), tuple((body_id, 1.0) for body_id in sorted(opened_bodies)), _state_hash(position, activations))
    return DynamicInferenceResult(prompt.prompt_id, disposition, initial, final, tuple(candidates), selected, tuple(trace), tuple(frontier_trace), tuple(sorted(opened_bodies)), coverage, (), ())
