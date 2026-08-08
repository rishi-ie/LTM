from __future__ import annotations

import json
import shutil
import tomllib
from pathlib import Path

from ltm import audit

ROOT = Path(__file__).resolve().parents[2]


def test_experiment_registry_is_complete_and_unique():
    registry = json.loads((ROOT / "docs/experiments/registry.json").read_text())
    rows = registry["experiments"]
    identifiers = [row["experiment_id"] for row in rows]
    assert len(identifiers) == len(set(identifiers))
    assert {row["status"] for row in rows} <= set(registry["status_values"])
    assert all(audit._REGISTRY_KEYS <= row.keys() for row in rows)
    for row in rows:
        for key in (
            "package_path",
            "test_path",
            "config_path",
            "specification_path",
            "report_path",
        ):
            if row[key] is not None:
                assert (ROOT / row[key]).exists(), (row["experiment_id"], key)


def test_experiment_summary_and_chain_cover_registry():
    result = audit._registry_audit(ROOT)
    assert result["count"] == 51
    assert result["summary_missing_ids"] == []
    assert result["chain_inconsistencies"] == []


def test_component_internals_has_all_required_components():
    result = audit._registry_audit(ROOT)
    assert result["missing_component_headings"] == []
    assert result["missing_maturity_labels"] == []


def test_architecture_manifest_matches_normative_inputs():
    assert audit._lock_mismatches(ROOT) == []


def test_architecture_manifest_detects_changed_input(tmp_path: Path):
    for relative in audit._LOCK_FILES:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    audit.write_architecture_manifest(tmp_path)
    assert audit._lock_mismatches(tmp_path) == []
    lock = tmp_path / "docs/architecture/architecture-lock-v1.md"
    lock.write_text(lock.read_text() + "\nchanged\n")
    assert str(audit._LOCK_FILES[0]) in audit._lock_mismatches(tmp_path)


def test_python_metadata_and_lock_are_canonical():
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert metadata["project"]["name"] == "latent-topology-models"
    assert metadata["project"]["requires-python"] == ">=3.11,<3.12"
    lock = (ROOT / "requirements/py311-macos.lock").read_text()
    assert "git+" not in lock
    assert "file:" not in lock
    assert "-e " not in lock
    assert "ltm-poc" not in lock
