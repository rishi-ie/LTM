from __future__ import annotations

import json
from pathlib import Path

import pytest

from ltm.local_archive import build_plan, execute, plan, restore, verify


def _fixture(root: Path) -> None:
    (root / "workspaces/large").mkdir(parents=True)
    (root / "workspaces/large/data.bin").write_bytes(b"large-data")
    (root / "workspaces/small").mkdir(parents=True)
    (root / "workspaces/small/data.txt").write_text("small")
    (root / ".models/keep").mkdir(parents=True)
    (root / ".models/keep/model.bin").write_bytes(b"keep")
    (root / ".models/old").mkdir(parents=True)
    (root / ".models/old/model.bin").write_bytes(b"old")
    (root / ".models/model-manifest.json").write_text(json.dumps({"models": [{"name": "keep"}]}))


def test_plan_threshold_and_model_allowlist(tmp_path: Path):
    _fixture(tmp_path)
    value = build_plan(tmp_path, tmp_path / "archive", min_workspace_mib=0)
    sources = {entry["source_relative"] for entry in value["entries"]}
    assert "workspaces/large" in sources
    assert "workspaces/small" in sources
    assert ".models/old" in sources
    assert ".models/keep" not in sources


def test_atomic_move_verify_and_restore(tmp_path: Path):
    _fixture(tmp_path)
    plan_path = plan(tmp_path, tmp_path / "archive", min_workspace_mib=0)
    manifest_path = execute(tmp_path, plan_path)
    result = verify(tmp_path, tmp_path / "archive")
    assert result["verified"] is True
    assert not (tmp_path / "workspaces/large").exists()
    restore(tmp_path, tmp_path / "archive", "workspaces/large")
    assert (tmp_path / "workspaces/large/data.bin").read_bytes() == b"large-data"
    with pytest.raises(RuntimeError, match="restore target is occupied"):
        restore(tmp_path, tmp_path / "archive", "workspaces/large")
    assert manifest_path.exists()


def test_existing_destination_without_journal_is_refused(tmp_path: Path):
    _fixture(tmp_path)
    plan_path = plan(tmp_path, tmp_path / "archive", min_workspace_mib=0)
    (tmp_path / "archive").mkdir()
    with pytest.raises(RuntimeError, match="destination already exists"):
        execute(tmp_path, plan_path)


def test_tamper_is_detected(tmp_path: Path):
    _fixture(tmp_path)
    plan_path = plan(tmp_path, tmp_path / "archive", min_workspace_mib=0)
    execute(tmp_path, plan_path)
    (tmp_path / "archive/workspaces/large/data.bin").write_bytes(b"tampered")
    with pytest.raises(RuntimeError, match="mismatch"):
        verify(tmp_path, tmp_path / "archive")
