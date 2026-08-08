"""Public-only, bounded latent-guided exact equality search."""

from __future__ import annotations

import numpy as np
import torch

from ltm_inference_i3.formal import expression_hash, expression_size

from .dataset import feature
from .field import MathFieldIndex
from .formal import enumerate_body_applications
from .kernel import SearchKernel
from .schemas import FormalProofStep, MathematicalInferenceResult, SearchTraceEvent, TheoremProblem


def infer(problem: TheoremProblem, field: MathFieldIndex, model: SearchKernel, *, use_goal: bool = True, use_heuristic: bool = True, use_scorer: bool = True, fixed_frontier: bool = False, prefer_reductions: bool = False, use_content_index: bool = True, trace_sink=None) -> MathematicalInferenceResult:
    state_goal = feature(problem.goal if use_goal else problem.source)
    initial_frontier = (field.content_frontier(problem.source, problem.goal, problem.maximum_bodies) if use_content_index else None) or field.frontier(feature(problem.source), state_goal, problem.maximum_bodies, fixed=fixed_frontier)
    beam: list[tuple[object, tuple[FormalProofStep, ...], float]] = [(problem.source, (), 0.0)]
    visited = {expression_hash(problem.source)}; opened = set(initial_frontier); priorities: list[float] = []
    for search_step in range(problem.maximum_steps):
        candidates: list[tuple[float, object, tuple[FormalProofStep, ...], str]] = []
        for state, proof, path_cost in beam:
            if fixed_frontier:
                body_ids, retrieval_mode = initial_frontier, "fixed"
            else:
                exact_ids = field.content_frontier(state, problem.goal, problem.maximum_bodies) if use_content_index else None
                if exact_ids:
                    body_ids, retrieval_mode = exact_ids, "content_index"
                else:
                    body_ids, retrieval_mode = field.frontier(feature(state), state_goal, problem.maximum_bodies), "minimap"
            opened.update(body_ids)
            bodies = tuple(field.bodies[item] for item in body_ids if field.bodies[item].reality_key == problem.reality_key)
            if not bodies:
                continue
            legal: list[tuple[object, tuple[int, ...], bool, object]] = []
            for body in bodies:
                for path, reverse, after in enumerate_body_applications(state, body):
                    if expression_hash(after) not in visited:
                        legal.append((body, path, reverse, after))
                        if len(legal) >= 128:
                            break
                if len(legal) >= 128:
                    break
            if not legal:
                continue
            if prefer_reductions:
                # This optional standard-algebra convenience is deliberately
                # disabled for detour/cost-to-go experiments: those require
                # temporary expression growth to remain searchable.
                reductions = [item for item in legal if expression_size(item[3]) < expression_size(state)]
                if reductions:
                    legal = reductions
            state_row = torch.from_numpy(feature(state)[None, :]); goal_row = torch.from_numpy(state_goal[None, :])
            body_rows = torch.from_numpy(np.stack([field.vectors[item[0].vector_index] for item in legal]))
            with torch.no_grad():
                scores = model.body_score(state_row.expand(len(legal), -1), goal_row.expand(len(legal), -1), body_rows).tolist() if use_scorer else [0.0] * len(legal)
                after_rows = torch.from_numpy(np.stack([feature(item[3]) for item in legal]))
                heuristics = model.remaining_cost(after_rows, goal_row.expand(len(legal), -1)).tolist() if use_heuristic else [0.0] * len(legal)
            retained_rows = []
            for score, heuristic, (body, path, reverse, after) in sorted(zip(scores, heuristics, legal, strict=True), key=lambda item: (-item[0], item[2][0].body_id))[:16]:
                priority = path_cost + 1.0 + (max(0.0, float(heuristic)) if use_heuristic else 0.0) - .25 * float(score)
                step = FormalProofStep(body.body_id, path, reverse, state, after)
                candidates.append((priority, after, proof + (step,), body.body_id))
                retained_rows.append((body.body_id, path, reverse, expression_hash(after), float(score)))
            if trace_sink is not None:
                trace_sink(SearchTraceEvent(search_step, expression_hash(state), retrieval_mode, tuple(body_ids), len(legal), tuple(retained_rows), len(visited)))
        if not candidates:
            break
        candidates.sort(key=lambda item: (item[0], expression_hash(item[1]), item[3]))
        beam = []
        for priority, after, proof, _ in candidates:
            key = expression_hash(after)
            if key in visited:
                continue
            visited.add(key); priorities.append(priority)
            if after == problem.goal:
                return MathematicalInferenceResult(problem.problem_id, "proved", proof, tuple(sorted(opened)), len(visited), tuple(priorities), ())
            beam.append((after, proof, float(len(proof))))
            if len(beam) == 16:
                break
    return MathematicalInferenceResult(problem.problem_id, "unknown", (), tuple(sorted(opened)), len(visited), tuple(priorities), ("NO_VERIFIED_PATH",))
