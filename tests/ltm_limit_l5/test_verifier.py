from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from ltm_limit_l5.dataset import build_case
from ltm_limit_l5.evaluator import verify_result
from ltm_limit_l5.field import EquilibriumFieldIndex, build_minimap
from ltm_limit_l5.optimizer import optimize
from ltm_limit_l5.verifier import certify_result, verify_candidate


def _run(family: str, index: int = 25):
    generated = build_case(index, 1941, family=family)
    case = generated.public
    vectors = np.asarray(case.vector_table, dtype=np.float32)
    cells, summaries = build_minimap(case.bodies, case.units, vectors)
    field = EquilibriumFieldIndex(case.bodies, case.units, vectors, cells, summaries)
    return generated, certify_result(case, optimize(field, case.prompt))


@pytest.mark.parametrize(
    "family",
    (
        "one_body",
        "dependency_2_4",
        "dependency_5_8",
        "dependency_9_16",
        "conjunction",
        "weighted_contradiction",
        "balanced_contradiction",
        "alternatives",
        "unknown",
    ),
)
def test_post_convergence_support_is_independently_replayable(family: str) -> None:
    generated, result = _run(family)
    assert verify_result(generated.public, result), family


def test_support_tampering_fails_closed() -> None:
    generated, result = _run("dependency_2_4")
    candidate = result.candidates[0]
    with pytest.raises(ValueError):
        verify_candidate(
            generated.public,
            replace(candidate, supporting_body_ids=candidate.supporting_body_ids[:-1]),
        )
