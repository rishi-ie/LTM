"""Small relation-free pair potential and bounded energy relaxation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from torch import nn

from .index import BodyIndex
from .schemas import InferencePrompt, LatentCandidate, LatentInferenceResult, OptimizationStep


class PairPotential(nn.Module):
    def __init__(self, dimension: int = 384, hidden: int = 32) -> None:
        super().__init__()
        self.project = nn.Linear(dimension, hidden, bias=False)
        self.score = nn.Sequential(nn.Linear(hidden * 3 + 1, hidden), nn.Tanh(), nn.Linear(hidden, 1))

    def forward(self, source: torch.Tensor, target: torch.Tensor, phase_delta: torch.Tensor) -> torch.Tensor:
        src = self.project(source)
        dst = self.project(target)
        features = torch.cat((src, dst, src * dst, phase_delta), dim=-1)
        return self.score(features).squeeze(-1)


@dataclass(frozen=True, slots=True)
class KernelState:
    state_dict: dict[str, object]
    dimension: int
    hidden: int
    parameter_count: int


def parameter_count(model: nn.Module) -> int:
    return sum(parameter.numel() for parameter in model.parameters())


def pair_features(source: np.ndarray, target: np.ndarray, phase_delta: float = 1.0) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    return (
        torch.from_numpy(np.asarray(source, dtype=np.float32)).reshape(1, -1),
        torch.from_numpy(np.asarray(target, dtype=np.float32)).reshape(1, -1),
        torch.tensor([[phase_delta]], dtype=torch.float32),
    )


def train_kernel(index: BodyIndex, vectors: np.ndarray, steps: int, seed: int) -> tuple[PairPotential, list[float]]:
    torch.manual_seed(seed)
    torch.set_num_threads(4)
    model = PairPotential(vectors.shape[1])
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=0.01)
    rng = np.random.default_rng(seed)
    body_values = tuple(index.bodies.values())
    losses: list[float] = []
    model.train()
    for _step in range(steps):
        body = body_values[int(rng.integers(len(body_values)))]
        body_units = index.body_units(body)
        sources = [unit for unit in body_units if unit.phase_index == 0]
        targets = [unit for unit in body_units if unit.phase_index == 1]
        if not sources or not targets:
            continue
        source = torch.from_numpy(np.mean([vectors[unit.semantic_vector_ref] for unit in sources], axis=0)).reshape(1, -1).float()
        target = torch.from_numpy(vectors[targets[0].semantic_vector_ref]).reshape(1, -1).float()
        negative = torch.from_numpy(vectors[int(rng.integers(len(vectors))) ]).reshape(1, -1).float()
        delta = torch.ones((1, 1), dtype=torch.float32)
        positive = model(source, target, delta)
        corrupt = model(source, negative, delta)
        loss = torch.relu(0.5 - positive + corrupt).mean()
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        losses.append(float(loss.detach()))
    return model.eval(), losses


def save_kernel(path: Path, model: PairPotential, losses: list[float], seed: int) -> dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"model": model.state_dict(), "losses": losses, "seed": seed, "parameters": parameter_count(model), "sha256": None}
    torch.save(payload, path)
    payload["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    torch.save(payload, path)
    return {"path": str(path), "parameters": parameter_count(model), "sha256": payload["sha256"], "final_loss": losses[-1] if losses else None}


def load_kernel(path: Path, dimension: int = 384) -> PairPotential:
    payload = torch.load(path, map_location="cpu", weights_only=False)
    model = PairPotential(dimension)
    model.load_state_dict(payload["model"])
    model.eval()
    return model


def infer(model: PairPotential, index: BodyIndex, vectors: np.ndarray, prompt: InferencePrompt, confidence: float = 0.70, margin_threshold: float = 0.05) -> LatentInferenceResult:
    active = {unit_id: 1.0 for unit_id in prompt.clamped_unit_ids}
    selected_bodies: dict[str, object] = {}
    trajectory: list[OptimizationStep] = []
    candidate_ids = set(prompt.candidate_atom_ids)
    energies: list[float] = []
    score_cache: dict[tuple[bytes, int], float] = {}
    for step in range(9):
        active_ids = tuple(active)
        for body in index.retrieve(active_ids, prompt.maximum_bodies):
            selected_bodies[body.body_id] = body
        active_by_identity: dict[str, float] = {}
        for active_id, value in active.items():
            unit = index.units.get(active_id)
            if unit is not None:
                active_by_identity[unit.identity_key] = max(active_by_identity.get(unit.identity_key, 0.0), value)
        signals: dict[str, float] = {candidate_id: 0.0 for candidate_id in candidate_ids}
        for body in selected_bodies.values():
            body_units = index.body_units(body)
            sources = [unit for unit in body_units if unit.phase_index == 0]
            targets = [unit for unit in body_units if unit.phase_index == 1 and unit.unit_id in candidate_ids]
            if not sources or not targets:
                continue
            # A phase transition carries identity/content state into the next
            # body.  Source occurrences are distinct records, so propagation
            # must match their stable semantic identity rather than requiring
            # the same occurrence ID to be reused across bodies.
            source_activation = min(active_by_identity.get(unit.identity_key, 0.0) for unit in sources)
            if source_activation <= 0:
                continue
            source_vector = np.mean([vectors[unit.semantic_vector_ref] for unit in sources], axis=0)
            missing = [(target, (source_vector.tobytes(), target.semantic_vector_ref)) for target in targets if (source_vector.tobytes(), target.semantic_vector_ref) not in score_cache]
            if missing:
                with torch.no_grad():
                    source_tensor = torch.from_numpy(np.repeat(source_vector[None, :], len(missing), axis=0)).float()
                    target_tensor = torch.from_numpy(np.asarray([vectors[target.semantic_vector_ref] for target, _ in missing], dtype=np.float32))
                    delta = torch.ones((len(missing), 1), dtype=torch.float32)
                    scores = model(source_tensor, target_tensor, delta).detach().numpy()
                for (target, key), score in zip(missing, scores):
                    score_cache[key] = float(score)
            for target in targets:
                score = score_cache[(source_vector.tobytes(), target.semantic_vector_ref)]
                signals[target.unit_id] = max(signals[target.unit_id], source_activation * float(1.0 / (1.0 + np.exp(-score))))
        previous = dict(active)
        for candidate_id, signal in signals.items():
            active[candidate_id] = float(np.clip(active.get(candidate_id, 0.0) + 0.15 * (signal - active.get(candidate_id, 0.0)), 0.0, 1.0))
        energy = float(sum((active.get(candidate_id, 0.0) - signals.get(candidate_id, 0.0)) ** 2 for candidate_id in candidate_ids))
        residual = float(max((abs(active.get(key, 0.0) - previous.get(key, 0.0)) for key in candidate_ids), default=0.0))
        energies.append(energy)
        trajectory.append(OptimizationStep(step, energy, residual, sum(value > 0.05 for value in active.values()), hashlib.sha256(repr(sorted(active.items())).encode()).hexdigest()))
    # The update is a projected contraction; numerical increases are a hard integrity failure.
    energy_increase = any(energies[index] > energies[index - 1] + 1e-7 for index in range(1, len(energies)))
    ranked = sorted(((candidate_id, active.get(candidate_id, 0.0)) for candidate_id in candidate_ids), key=lambda item: (-item[1], item[0]))
    candidates: list[LatentCandidate] = []
    for rank, (candidate_id, value) in enumerate(ranked[:8]):
        second = ranked[rank + 1][1] if rank + 1 < len(ranked) else 0.0
        candidates.append(LatentCandidate(candidate_id, value, value - second, tuple(sorted(selected_bodies)), (index.units[candidate_id].provenance_id,)))
    selected = candidates[0].atom_id if candidates and candidates[0].probability >= confidence and candidates[0].margin >= margin_threshold else None
    disposition = "candidate" if selected else ("ambiguous" if candidates and candidates[0].probability >= confidence / 2 else "unknown")
    failures = ("ENERGY_INCREASE",) if energy_increase else ()
    if energy_increase:
        disposition = "quarantine"
        selected = None
    return LatentInferenceResult(prompt.prompt_id, disposition, tuple(candidates), selected, tuple(trajectory), len(selected_bodies), len(active), failures, ())
