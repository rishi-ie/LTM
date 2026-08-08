"""Evaluator-owned shortest-path certification for concrete body fields."""

from __future__ import annotations

from ltm_inference_i3.formal import expression_hash
from ltm_inference_i31.formal import enumerate_body_applications
from ltm_inference_i31.schemas import MathematicalBody


def shortest_depth(source, goal, bodies: tuple[MathematicalBody, ...], maximum: int = 64) -> int | None:
    """Return the first exact rewrite depth, or None within the bound."""
    frontier = {expression_hash(source): source}
    visited = set(frontier)
    for depth in range(maximum + 1):
        if expression_hash(goal) in frontier:
            return depth
        following = {}
        for state in frontier.values():
            for body in bodies:
                for _path, _reverse, after in enumerate_body_applications(state, body):
                    key = expression_hash(after)
                    if key not in visited:
                        visited.add(key)
                        following[key] = after
        frontier = following
        if not frontier:
            return None
    return None
