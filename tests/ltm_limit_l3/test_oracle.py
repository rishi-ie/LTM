from __future__ import annotations

from ltm_limit_l3.generator import grounded_case
from ltm_limit_l3.oracle import shortest_depth
from ltm_limit_l3.runtime import _runtime_body


def test_grounded_certificate_is_independently_shortest():
    case = grounded_case(8, 7)
    bodies = tuple(_runtime_body(body, index) for index, body in enumerate(case.bodies))
    assert shortest_depth(case.question.theorem_problem.source, case.question.theorem_problem.goal, bodies, 8) == 8
