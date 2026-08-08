from __future__ import annotations

from pathlib import Path

from topology_g11.generator import build
from topology_g11.runtime import run_case


def test_lifecycle_preserves_base_and_clears_overlay(tmp_path: Path) -> None:
    result = run_case(build(1739, 1)[0], tmp_path, controls=True)
    assert result["base_unchanged"]
    assert result["restart_equal"]
    assert result["deleted"]["claims"] == ()
    assert result["post_clear_session"]["status"] == "unknown"
    assert result["post_clear_base"]["status"] == "verified"


def test_assistant_is_not_normal_evidence(tmp_path: Path) -> None:
    result = run_case(build(1739, 1)[0], tmp_path, controls=True)
    assert result["deleted"]["claims"] == ()
    assert result["assistant_promoted"]["claims"]
    assert result["summary_control"]["status"] == "unknown"


def test_episode_reopens_and_preserves_scope(tmp_path: Path) -> None:
    result = run_case(build(1739, 1)[0], tmp_path, controls=True)
    records = {row["kind"]: row["result"] for row in result["records"] if row["kind"] != "restart"}
    assert records["episode"]["reopened_episode_ids"]
    assert records["scope"]["status"] == "unknown"
    assert records["preference"]["preferences"] == ("brief",)
