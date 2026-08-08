from pathlib import Path

from ltm_inference_i31.prompt_audit import run


def test_prompt_audit_replays_and_realizes():
    workspace = Path("/tmp/ltm-i31-prompt-audit-test")
    checkpoint = Path("workspaces/ltm-inference-i3-1-r13/selected-kernel.pt")
    record = run(workspace, checkpoint)
    assert record.inference.disposition == "proved"
    assert tuple(item.body_id for item in record.inference.proof) == (
        "standard-v1:axiom:ring.mul_one",
        "standard-v1:axiom:ring.add_zero",
    )
    assert record.replay_valid
    assert record.field_semantic_hash
    assert record.mumbrane_semantic_hash
    assert record.decoder_text
    assert all(item[2] for item in record.controls)
