"""Frozen I3.1 proof-search handoff for compiled L3 bodies."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import torch

from ltm.local_archive import resolve_archived_path
from ltm_inference_i31.dataset import feature
from ltm_inference_i31.field import MathFieldIndex, build_field
from ltm_inference_i31.formal import body_hash, verify_proof
from ltm_inference_i31.kernel import SearchKernel
from ltm_inference_i31.runtime import infer
from ltm_inference_i31.schemas import MathematicalBody

from .oracle import shortest_depth
from .schemas import L3Body, L3Observation, L3Problem


def _model(checkpoint: Path) -> SearchKernel:
    model = SearchKernel()
    model.load_state_dict(torch.load(resolve_archived_path(checkpoint), map_location="cpu", weights_only=True))
    return model.eval()


def _runtime_body(body: L3Body, index: int) -> MathematicalBody:
    raw = MathematicalBody(body.body_id, body.reality_key, body.left, body.right, body.source_hash, index)
    return MathematicalBody(body.body_id, body.reality_key, body.left, body.right, body_hash(raw), index)


def build_runtime_field(bodies: tuple[L3Body, ...]) -> MathFieldIndex:
    """Compile archive-backed bodies once, then execute only numeric/AST state."""
    runtime_bodies = tuple(_runtime_body(body, index) for index, body in enumerate(bodies))
    vectors = np.asarray([np.concatenate((feature(item.left), feature(item.right))) for item in runtime_bodies], dtype=np.float32)
    return MathFieldIndex(runtime_bodies, vectors, build_field(runtime_bodies, vectors))


def run_case(
    problem: L3Problem,
    bodies: tuple[L3Body, ...],
    checkpoint: Path,
    *,
    field: MathFieldIndex | None = None,
    model: SearchKernel | None = None,
    use_goal: bool = True,
    use_heuristic: bool = True,
    use_scorer: bool = True,
    fixed_frontier: bool = False,
    use_content_index: bool = True,
) -> L3Observation:
    if problem.question.theorem_problem is None or not set(problem.body_ids).issubset({body.body_id for body in bodies}):
        return L3Observation(problem.case_id, problem.panel, "clarification_required", 0, False, False, 0, 0, 0.0, "COMPILER_INVALID")
    active_field = field or build_runtime_field(bodies)
    active_field.reset_counter()
    started = time.perf_counter()
    result = infer(
        problem.question.theorem_problem,
        active_field,
        model or _model(checkpoint),
        use_goal=use_goal,
        use_heuristic=use_heuristic,
        use_scorer=use_scorer,
        fixed_frontier=fixed_frontier,
        prefer_reductions=False,
        use_content_index=use_content_index,
    )
    runtime_ms = (time.perf_counter() - started) * 1000
    body_map = active_field.bodies
    valid = bool(result.disposition == "proved" and verify_proof(problem.question.theorem_problem.source, problem.question.theorem_problem.goal, result.proof, body_map, problem.question.theorem_problem.reality_key))
    failure = "NONE" if valid else ("REQUIRED_BODY_NOT_RETRIEVED" if not result.opened_body_ids else "PROOF_REPLAY_FAILURE")
    return L3Observation(
        problem.case_id,
        problem.panel,
        result.disposition,
        len(result.proof),
        valid,
        True,
        len(result.opened_body_ids),
        result.state_count,
        runtime_ms,
        failure,
        tuple(step.body_id for step in result.proof),
    )


def certify_shortest(problem: L3Problem) -> int | None:
    bodies = tuple(_runtime_body(body, index) for index, body in enumerate(problem.bodies))
    return shortest_depth(problem.question.theorem_problem.source, problem.question.theorem_problem.goal, bodies, problem.expected_depth) if problem.question.theorem_problem else None
