from __future__ import annotations

import hashlib
import random
from collections.abc import Iterator

from ltm_inference_i3.formal import c, e
from ltm_inference_i31.dataset import atom
from ltm_inference_i31.formal import body_hash
from ltm_inference_i31.schemas import MathematicalBody, TheoremProblem

from .schemas import LimitCase


def _token(seed: str, index: int) -> str:
    return hashlib.sha256(f"{seed}:{index}".encode()).hexdigest()[:24]


def _body(case_id: str, index: int, left, right, vector_index: int) -> MathematicalBody:
    body = MathematicalBody(f"body:{_token(case_id, index)}", "standard-v1", left, right, "", vector_index)
    return MathematicalBody(body.body_id, body.reality_key, body.left, body.right, body_hash(body), vector_index)


def traversal_case(depth: int, serial: int, branches: int, *, answerable: bool = True) -> LimitCase:
    case_id = f"traversal:{serial:06d}:{depth:03d}:{branches:02d}"
    states = [atom(f"opaque:{_token(case_id, i)}") for i in range(depth + 1)]
    bodies: list[MathematicalBody] = []
    for index in range(depth):
        bodies.append(_body(case_id, index, states[index], states[index + 1], len(bodies)))
        for branch in range(branches - 1):
            dead = atom(f"dead:{_token(case_id, index * 100 + branch)}")
            bodies.append(_body(case_id, depth + index * branches + branch, states[index], dead, len(bodies)))
    goal = states[-1] if answerable else atom(f"unknown:{_token(case_id, 999999)}")
    problem = TheoremProblem(case_id, "standard-v1", states[0], goal, 64, 64)
    random.Random(91000 + serial * 17 + depth).shuffle(bodies)
    return LimitCase(case_id, "traversal", depth, problem, tuple(bodies), branches, answerable)


def formal_case(depth: int, serial: int, *, answerable: bool = True) -> LimitCase:
    case_id = f"formal:{serial:06d}:{depth:03d}"
    current = c(5)
    states = [current]
    for index in range(depth):
        current = e("mul", current, c(1)) if index % 2 else e("add", current, c(0))
        states.append(current)
    bodies = [_body(case_id, index, states[index], states[index + 1], index) for index in range(depth)]
    for index in range(depth):
        # Dead alternatives terminate after one exact application; they must
        # not create recursive AST growth that measures a generator bug.
        distractor = atom(f"dead:{_token(case_id, 500000 + index)}")
        bodies.append(_body(case_id, depth + index, states[index], distractor, len(bodies)))
    goal = states[-1] if answerable else e("add", states[-1], c(7))
    problem = TheoremProblem(case_id, "standard-v1", states[0], goal, 64, 64)
    random.Random(72000 + serial).shuffle(bodies)
    return LimitCase(case_id, "formal", depth, problem, tuple(bodies), 2, answerable)


def build_suite(*, base_per_depth: int = 20, reserved_per_depth: int = 80) -> tuple[LimitCase, ...]:
    cases: list[LimitCase] = []
    serial = 0
    for depth in range(1, 65):
        for index in range(base_per_depth):
            branches = (1, 4, 16, 32)[index % 4]
            cases.extend((traversal_case(depth, serial, branches),)); serial += 1
            cases.extend((formal_case(depth, serial),)); serial += 1
    for depth in range(1, 65):
        for index in range(reserved_per_depth):
            branches = (1, 4, 16, 32)[index % 4]
            cases.extend((traversal_case(depth, serial, branches),)); serial += 1
            cases.extend((formal_case(depth, serial),)); serial += 1
    for depth in range(65, 129):
        cases.extend((formal_case(depth, serial),)); serial += 1
        cases.extend((traversal_case(depth, serial, 4),)); serial += 1
    for index in range(256):
        depth = 1 + index % 64
        cases.extend((formal_case(depth, serial, answerable=False),)); serial += 1
        cases.extend((traversal_case(depth, serial, 4, answerable=False),)); serial += 1
    return tuple(cases)


def iter_suite(*, base_per_depth: int = 20, reserved_per_depth: int = 80) -> Iterator[LimitCase]:
    serial = 0
    for depth in range(1, 65):
        for index in range(base_per_depth):
            branches = (1, 4, 16, 32)[index % 4]
            yield traversal_case(depth, serial, branches); serial += 1
            yield formal_case(depth, serial); serial += 1
    for depth in range(1, 65):
        for index in range(reserved_per_depth):
            branches = (1, 4, 16, 32)[index % 4]
            yield traversal_case(depth, serial, branches); serial += 1
            yield formal_case(depth, serial); serial += 1
    for depth in range(65, 129):
        yield formal_case(depth, serial); serial += 1
        yield traversal_case(depth, serial, 4); serial += 1
    for index in range(256):
        depth = 1 + index % 64
        yield formal_case(depth, serial, answerable=False); serial += 1
        yield traversal_case(depth, serial, 4, answerable=False); serial += 1


def case_obj(case: LimitCase) -> dict[str, object]:
    return {
        "case_id": case.case_id,
        "panel": case.panel,
        "certified_depth": case.certified_depth,
        "branching_factor": case.branching_factor,
        "answerable": case.answerable,
        "serial": int(case.case_id.split(":")[1]),
    }
