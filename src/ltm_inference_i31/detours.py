"""Non-leaky detour fixtures for the next I3.1 corpus revision.

The runtime sees only opaque terms and signed bodies.  Shortest proof distance
is computed here for evaluator/training use and is never attached to a public
problem, body, minimap cell, or vector.
"""

from __future__ import annotations

import hashlib
from collections import deque
from dataclasses import dataclass

from ltm_inference_i3.schemas import FormalExpression

from .formal import body_hash
from .schemas import MathematicalBody


@dataclass(frozen=True, slots=True)
class DetourFixture:
    reality_key: str
    source: FormalExpression
    goal: FormalExpression
    bodies: tuple[MathematicalBody, ...]


def _opaque(seed: str, index: int) -> FormalExpression:
    value = hashlib.sha256(f"{seed}:{index}".encode()).hexdigest()[:24]
    return FormalExpression("atom", value=f"opaque:{value}")


def build_detour_fixture(seed: str = "i31-detour") -> DetourFixture:
    """One 3-hop route, one longer valid route, and 22 dead-end choices."""
    nodes = tuple(_opaque(seed, index) for index in range(40))
    source, goal = nodes[0], nodes[1]
    edges = ((0, 2), (2, 3), (3, 1), (0, 4), (4, 5), (5, 6), (6, 7), (7, 8), (8, 1))
    edges += tuple((0, index) for index in range(9, 31))
    bodies = []
    for index, (left, right) in enumerate(edges):
        body = MathematicalBody(f"detour:{index:03d}", "standard-v1", nodes[left], nodes[right], "", index)
        bodies.append(MathematicalBody(body.body_id, body.reality_key, body.left, body.right, body_hash(body), index))
    return DetourFixture("standard-v1", source, goal, tuple(bodies))


def shortest_distance(fixture: DetourFixture, source: FormalExpression | None = None) -> int | None:
    """Evaluator-only exact graph distance over the supplied body set."""
    start = fixture.source if source is None else source
    queue = deque([(start, 0)])
    seen = {start}
    outgoing: dict[FormalExpression, list[FormalExpression]] = {}
    for body in fixture.bodies:
        outgoing.setdefault(body.left, []).append(body.right)
    while queue:
        current, distance = queue.popleft()
        if current == fixture.goal:
            return distance
        for next_value in outgoing.get(current, ()):
            if next_value not in seen:
                seen.add(next_value); queue.append((next_value, distance + 1))
    return None
