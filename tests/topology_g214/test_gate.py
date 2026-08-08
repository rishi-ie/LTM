from topology_g213.inference import Prediction
from topology_g214.dataset import generate
from topology_g214.gate import regrade
from topology_g214.schemas import (
    AcceptanceEvidence,
    CandidateResolution,
    GatedConversationPrediction,
    HeadConfidence,
)


def test_fresh_gate_suite_has_bounded_candidates():
    cases = generate("calibration")
    assert len(cases) == 2400
    assert max(len(item.candidates) for item in cases) <= 16
    assert sum(item.case.reference_state == "ambiguous" for item in cases) == 200


def test_candidate_resolution_contract_is_immutable():
    item = CandidateResolution("reference", "ambiguous", None, ("a", "b"), 1.0, 0.0, 2)
    assert item.margin == 0.0


def test_acceptance_gate_is_monotonic():
    prediction = Prediction("source", "statement", "none", "none", "positive", "asserted", "session", "clarification_required", (), (), 0.99)
    evidence = AcceptanceEvidence("source", (HeadConfidence("act", "statement", 0.99, 0.9),), (), 0.99, 0.9, (), ("MODEL_NOT_ACCEPT",), "g2.14-gate/1", "hash")
    gated = GatedConversationPrediction("source", prediction, evidence, "clarification_required", (), ("MODEL_NOT_ACCEPT",))
    downgraded = regrade(gated, confidence_threshold=0.5, margin_threshold=0.02, identity_confidence=0.7, identity_margin=0.05)
    assert downgraded.final_disposition == "clarification_required"


def test_candidate_limit_is_strict():
    assert max(len(item.candidates) for item in generate("locked")) <= 16
