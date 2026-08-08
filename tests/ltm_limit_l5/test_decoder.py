from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from ltm_limit_l5.dataset import build_case
from ltm_limit_l5.decoder import authorize, realize
from ltm_limit_l5.evaluator import certificate_for, source_normalized_outcome
from ltm_limit_l5.field import EquilibriumFieldIndex, build_minimap
from ltm_limit_l5.optimizer import optimize
from ltm_limit_l5.schemas import EquilibriumCandidate, FieldEquilibriumResult, LatentModeState
from ltm_limit_l5.verifier import certify_result


def _verified_result():
    case = build_case(0, 5, family="one_body").public
    oracle = source_normalized_outcome(case)
    row = oracle.candidates[0]
    candidate = EquilibriumCandidate(
        row.unit_ids[0], row.semantic_key, row.polarity, 1.0, 1.0,
        row.body_ids, row.source_keys, row.provenance_ids,
    )
    certificate = certificate_for(case, candidate)
    mode = LatentModeState("mode:0", case.prompt.anchor_position, (), 1.0, 1, (), "0" * 64)
    result = FieldEquilibriumResult(
        case.case_id, "candidate", (mode,), (mode,), (candidate,), candidate.unit_id,
        (), (), (certificate,), "certified", (),
    )
    return result, candidate


def test_decoder_sees_only_verified_authorized_labels() -> None:
    result, candidate = _verified_result()
    output = realize(authorize(result), {candidate.semantic_key: "verified answer"})
    assert output.text == "verified answer"
    assert output.authorized_unit_ids == (candidate.unit_id,)


def test_decoder_rejects_unverified_selected_candidate() -> None:
    result, _ = _verified_result()
    with pytest.raises(ValueError, match="UNVERIFIED"):
        authorize(replace(result, certificates=()))


def test_decoder_authorizes_only_selected_candidate_when_opposition_is_verified() -> None:
    case = build_case(0, 7, family="weighted_contradiction").public
    cells, summaries = build_minimap(case.bodies, case.units, np.asarray(case.vector_table))
    index = EquilibriumFieldIndex(
        case.bodies, case.units, np.asarray(case.vector_table), cells, summaries
    )
    result = certify_result(case, optimize(index, case.prompt))
    view = authorize(result)
    assert result.disposition == "candidate"
    assert len(result.certificates) == 2
    assert tuple(item.unit_id for item in view.candidates) == (result.selected_candidate_id,)
