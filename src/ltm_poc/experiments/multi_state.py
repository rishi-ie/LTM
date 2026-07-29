"""Deterministic MMR and multi-state latent optimization."""

from dataclasses import dataclass
from typing import Literal

import numpy as np
from pydantic import BaseModel

from ltm_poc.field import LatentField
from ltm_poc.schemas import ChunkRecord


class SetOptimizationStep(BaseModel):
    step: int
    set_evaluations: int
    slot_energy_evaluations: int
    energy: float
    gradient_norm: float
    state_delta: float
    nearest_chunk_ids: list[str]


class SetOptimizationResult(BaseModel):
    termination: Literal["converged_state", "max_steps", "hard_budget", "non_finite"]
    update_steps: int
    set_evaluations: int
    slot_energy_evaluations: int
    initial_energy: float
    final_energy: float
    final_states: list[list[float]]
    trace: list[SetOptimizationStep]


class SetEvidenceItem(BaseModel):
    rank: int
    slot: int
    chunk_id: str
    source_path: str
    state_cosine: float
    query_cosine: float
    text: str


def _unit(vector: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vector)
    if not np.isfinite(norm) or norm == 0:
        raise ValueError("cannot normalize non-finite or zero vector")
    return vector / norm


@dataclass(frozen=True)
class SetOptimizerConfig:
    slots: int = 4
    seed_pool: int = 16
    mmr_lambda: float = 0.7
    seed_mix: float = 0.15
    diversity_weight: float = 0.75
    similarity_cap: float = 0.75
    steps: int = 8
    hard_set_evaluations: int = 16
    learning_rate: float = 0.05
    backtracking_retries: int = 3
    state_tolerance: float = 1e-4
    energy_tolerance: float = 1e-4

    def __post_init__(self) -> None:
        if self.slots < 1 or self.seed_pool < self.slots:
            raise ValueError("seed_pool must contain every slot")
        if not 0 < self.mmr_lambda <= 1 or not 0 < self.seed_mix < 1:
            raise ValueError("MMR lambda and seed mixture must be in (0, 1)")
        if self.diversity_weight < 0 or not -1 < self.similarity_cap < 1:
            raise ValueError("invalid diversity settings")
        if self.steps < 1 or self.hard_set_evaluations < self.steps + 1:
            raise ValueError("invalid set evaluation budget")


def mmr_indices(
    query: np.ndarray,
    vectors: np.ndarray,
    chunks: list[ChunkRecord],
    limit: int,
    seed_pool: int = 16,
    mmr_lambda: float = 0.7,
) -> list[int]:
    """Select from the direct top pool with stable chunk-ID tie breaking."""
    scores = vectors @ query
    pool = sorted(
        range(len(chunks)),
        key=lambda index: (-float(scores[index]), chunks[index].chunk_id),
    )[:seed_pool]
    selected: list[int] = []
    while pool and len(selected) < limit:

        def key(index: int) -> tuple[float, str]:
            redundancy = (
                max(float(vectors[index] @ vectors[chosen]) for chosen in selected)
                if selected
                else 0.0
            )
            score = mmr_lambda * float(scores[index]) - (1 - mmr_lambda) * redundancy
            return -score, chunks[index].chunk_id

        chosen = min(pool, key=key)
        selected.append(chosen)
        pool.remove(chosen)
    return selected


def initialize_states(
    field: LatentField,
    chunks: list[ChunkRecord],
    config: SetOptimizerConfig,
    query_only: bool = False,
) -> np.ndarray:
    if query_only:
        return np.repeat(field.query[None, :], config.slots, axis=0)
    seeds = mmr_indices(
        field.query,
        field.vectors,
        chunks,
        config.slots,
        config.seed_pool,
        config.mmr_lambda,
    )
    return np.asarray(
        [
            _unit(
                (1 - config.seed_mix) * field.query
                + config.seed_mix * field.vectors[index]
            )
            for index in seeds
        ],
        dtype=np.float64,
    )


@dataclass(frozen=True)
class LatentSetField:
    base: LatentField
    diversity_weight: float
    similarity_cap: float

    def energy_and_gradient(self, states: np.ndarray) -> tuple[float, np.ndarray]:
        if states.ndim != 2 or states.shape[1] != 384:
            raise ValueError("set states must have shape (slots, 384)")
        if not np.allclose(np.linalg.norm(states, axis=1), 1.0, atol=1e-6):
            raise ValueError("every set state must be unit normalized")
        slots = len(states)
        energies: list[float] = []
        gradients = np.empty_like(states, dtype=np.float64)
        for index, state in enumerate(states):
            energy, gradient = self.base.energy_and_gradient(state)
            energies.append(energy)
            gradients[index] = gradient / slots
        pair_count = max(1, slots * (slots - 1) // 2)
        diversity = 0.0
        for left in range(slots):
            for right in range(left + 1, slots):
                excess = float(states[left] @ states[right]) - self.similarity_cap
                if excess <= 0:
                    continue
                scale = self.diversity_weight / pair_count
                diversity += scale * excess**2
                gradients[left] += 2 * scale * excess * states[right]
                gradients[right] += 2 * scale * excess * states[left]
        return float(np.mean(energies) + diversity), gradients


def optimize_set(
    field: LatentSetField,
    initial_states: np.ndarray,
    config: SetOptimizerConfig,
) -> SetOptimizationResult:
    states = initial_states.copy()
    energy, gradient = field.energy_and_gradient(states)
    initial_energy = energy
    evaluations = 1
    trace: list[SetOptimizationStep] = []
    termination = "max_steps"
    for step in range(1, config.steps + 1):
        tangent = gradient - (gradient * states).sum(axis=1, keepdims=True) * states
        learning_rate = config.learning_rate
        accepted = False
        for _ in range(config.backtracking_retries):
            candidates = np.asarray(
                [
                    _unit(state - learning_rate * grad)
                    for state, grad in zip(states, tangent)
                ]
            )
            candidate_energy, candidate_gradient = field.energy_and_gradient(candidates)
            evaluations += 1
            if candidate_energy <= energy + config.energy_tolerance:
                accepted = True
                break
            if evaluations >= config.hard_set_evaluations:
                break
            learning_rate *= 0.5
        if not accepted:
            termination = (
                "hard_budget"
                if evaluations >= config.hard_set_evaluations
                else "max_steps"
            )
            break
        delta = float(np.linalg.norm(candidates - states))
        states, energy, gradient = candidates, candidate_energy, candidate_gradient
        trace.append(
            SetOptimizationStep(
                step=step,
                set_evaluations=evaluations,
                slot_energy_evaluations=len(states) * evaluations,
                energy=energy,
                gradient_norm=float(np.linalg.norm(tangent)),
                state_delta=delta,
                nearest_chunk_ids=[],
            )
        )
        if delta <= config.state_tolerance:
            termination = "converged_state"
            break
        if evaluations >= config.hard_set_evaluations:
            termination = "hard_budget"
            break
    return SetOptimizationResult(
        termination=termination,
        update_steps=len(trace),
        set_evaluations=evaluations,
        slot_energy_evaluations=len(states) * evaluations,
        initial_energy=initial_energy,
        final_energy=energy,
        final_states=states.tolist(),
        trace=trace,
    )


def resolve_set_evidence(
    field: LatentField, states: np.ndarray, limit: int
) -> list[SetEvidenceItem]:
    """Resolve distinct evidence, one per slot before globally filling."""
    scores = states @ field.vectors.T
    chosen: list[tuple[int, int]] = []
    used: set[int] = set()
    for slot in range(len(states)):
        candidates = sorted(
            range(len(field.evidence)),
            key=lambda index: (
                -float(scores[slot, index]),
                field.evidence[index].chunk_id,
            ),
        )
        index = next(candidate for candidate in candidates if candidate not in used)
        chosen.append((slot, index))
        used.add(index)
        if len(chosen) == limit:
            break
    if len(chosen) < limit:
        remaining = sorted(
            (
                (
                    -float(scores[slot, index]),
                    field.evidence[index].chunk_id,
                    slot,
                    index,
                )
                for slot in range(len(states))
                for index in range(len(field.evidence))
                if index not in used
            )
        )
        for _, _, slot, index in remaining:
            if index in used:
                continue
            chosen.append((slot, index))
            used.add(index)
            if len(chosen) >= limit:
                break
    return [
        SetEvidenceItem(
            rank=rank,
            slot=slot,
            chunk_id=field.evidence[index].chunk_id,
            source_path=field.evidence[index].source_path,
            state_cosine=float(scores[slot, index]),
            query_cosine=float(field.query @ field.vectors[index]),
            text=field.evidence[index].text,
        )
        for rank, (slot, index) in enumerate(chosen, start=1)
    ]
