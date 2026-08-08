from pathlib import Path

from ltm_r2 import evaluate


def test_small_lifecycle_has_deterministic_semantic_replay(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(evaluate, "DEVELOPMENT_BODIES", 8)
    monkeypatch.setattr(evaluate, "LOCKED_BODIES", 16)
    evaluate.model_check(tmp_path)
    evaluate.build_development(tmp_path)
    development = evaluate.development(tmp_path)
    assert development["all_pass"]
    evaluate.freeze(tmp_path)
    evaluate.locked_suite_build(tmp_path)
    result = evaluate.evaluate(tmp_path)
    verification = evaluate.verify(tmp_path)
    assert result["classification"] == "LTM-R2-A — UNIVERSAL MUMBRANE PASS"
    assert verification["semantic_replay"]
