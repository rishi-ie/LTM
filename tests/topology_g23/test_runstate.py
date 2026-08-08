from pathlib import Path

import pytest

from topology_g23.runstate import begin_stage, checkpoint_stage, load_stage


def test_incomplete_stage_resumes_only_with_same_inputs(tmp_path: Path) -> None:
    state = begin_stage(tmp_path, "development", {"source": "a"}, "r1")
    checkpoint_stage(tmp_path, state, cursor={"epoch": 2, "batch": 4})
    restored = begin_stage(tmp_path, "development", {"source": "a"}, "ignored")
    assert restored.status == "running"
    assert dict(restored.cursor) == {"batch": 4, "epoch": 2}
    with pytest.raises(RuntimeError, match="upstream hash changed"):
        begin_stage(tmp_path, "development", {"source": "b"}, "r2")


def test_completed_stage_is_idempotent(tmp_path: Path) -> None:
    state = begin_stage(tmp_path, "locked-evaluation", {"frozen": "x"}, "r1")
    completed = checkpoint_stage(tmp_path, state, status="completed")
    assert load_stage(tmp_path, "locked-evaluation") == completed
    assert begin_stage(tmp_path, "locked-evaluation", {"frozen": "x"}, "r2").status == "completed"
