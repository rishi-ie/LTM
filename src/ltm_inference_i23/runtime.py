"""Public-only I2.3 inference. This module deliberately has no gold loader."""

from __future__ import annotations

import hashlib

import numpy as np

from .field import PublicField
from .schemas import OptimizationStep, RuntimePrompt, RuntimeResult


def _hash(value: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(value, dtype=np.float32).tobytes()).hexdigest()


def _energy(anchor: np.ndarray, state: np.ndarray, cumulative_support: float) -> float:
    """Profile energy: accumulated source support plus bounded anchor drift."""
    return -cumulative_support + .05 * (1.0 - float(np.dot(anchor, state)))


def infer(field: PublicField, model: object, prompt: RuntimePrompt, *, source_threshold: float = .995) -> RuntimeResult:
    """Move only through observed source-compatible bodies under bounded backtracking."""
    anchor = field.prompt_state(prompt.clamped_unit_ids, model)  # type: ignore[arg-type]
    state = anchor.copy()
    support = 0.0
    trace: list[OptimizationStep] = []
    visited: list[str] = []
    last_candidate: str | None = None
    minimum_retrieval_margin = 1.0
    minimum_source_score = 1.0
    for step in range(prompt.maximum_steps):
        # One macro update may combine two source-backed body forces. This keeps
        # the 32 optimisation-update budget while retaining the certified 64-body
        # detailed-access budget. Each inner force has its own backtracking test.
        opened_ids: list[str] = []
        last_body: str | None = None
        macro_accepted = False
        halted = False
        for _ in range(2):
            frontier, opened, retrieval_margin = field.frontier_with_margin(state, prompt.scope_key, prompt.maximum_bodies)
            opened_ids.extend(opened)
            minimum_retrieval_margin = min(minimum_retrieval_margin, retrieval_margin)
            if not frontier:
                halted = True
                break
            body_id = frontier[0]
            source = field.source_state[body_id]
            score = float(np.dot(state, source))
            minimum_source_score = min(minimum_source_score, score)
            if score < source_threshold:
                halted = True
                break
            outcome = field.outcome_state[body_id]
            old_energy = _energy(anchor, state, support)
            # Gradient of ||z-outcome||² has its minimiser at the observed outcome.
            # Backtracking makes each detailed-body force explicit and fail-closed.
            learning_rate = .5
            accepted = False
            proposal = state
            while learning_rate >= 1.0 / 32.0:
                trial = field._normalise(state - learning_rate * 2.0 * (state - outcome))
                if _energy(anchor, trial, support + score) <= old_energy + 1e-7:
                    proposal = trial
                    accepted = True
                    break
                learning_rate *= .5
            if not accepted:
                halted = True
                break
            state = proposal
            support += score
            visited.append(body_id)
            last_candidate = field.outcome_units[body_id].unit_id
            last_body = body_id
            macro_accepted = True
        trace.append(OptimizationStep(step, _energy(anchor, state, support), macro_accepted, last_body, tuple(dict.fromkeys(opened_ids)), _hash(state)))
        if halted:
            break
    final_frontier, _, final_margin = field.frontier_with_margin(state, prompt.scope_key, prompt.maximum_bodies)
    minimum_retrieval_margin = min(minimum_retrieval_margin, final_margin)
    best_final = max((float(np.dot(state, field.source_state[item])) for item in final_frontier), default=-1.0)
    confidence = max(0.0, min(1.0, minimum_source_score) * max(0.0, min(1.0, minimum_retrieval_margin * 20.0)))
    if last_candidate and best_final < source_threshold:
        return RuntimeResult(prompt.prompt_id, "candidate", last_candidate, ((last_candidate, confidence),), tuple(visited), tuple(trace), "certified")
    if not visited:
        return RuntimeResult(prompt.prompt_id, "unknown", None, (), (), tuple(trace), "certified")
    return RuntimeResult(prompt.prompt_id, "incomplete_frontier", None, ((last_candidate, 1.0),) if last_candidate else (), tuple(visited), tuple(trace), "incomplete_frontier")
