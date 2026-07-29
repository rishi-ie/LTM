"""Pinned model acquisition tests; no network or model weights required."""

import json
from pathlib import Path

import pytest

from ltm_poc import models


def test_catalog_is_pinned_and_uses_safe_patterns() -> None:
    for spec in (models.EMBEDDING_MODEL, models.DECODER_MODEL):
        assert len(spec.revision) == 40
        assert "*.safetensors" in spec.allow_patterns
        assert "*.bin" in spec.ignore_patterns


def test_download_writes_a_hashed_manifest(tmp_path: Path, monkeypatch) -> None:
    def fake_download(**kwargs: object) -> str:
        local_dir = kwargs["local_dir"]
        assert isinstance(local_dir, Path)
        local_dir.mkdir(parents=True)
        (local_dir / "model.safetensors").write_bytes(b"safe")
        (local_dir / ".cache").mkdir()
        (local_dir / ".cache" / "metadata").write_text("ignored", encoding="utf-8")
        return str(local_dir)

    monkeypatch.setattr(models, "snapshot_download", fake_download)
    manifest = models.download_models(tmp_path)

    saved = json.loads((tmp_path / "model-manifest.json").read_text(encoding="utf-8"))
    assert saved == manifest
    assert saved["models"][0]["files_sha256"]["model.safetensors"]
    hashed_files = saved["models"][0]["files_sha256"]
    assert all(not path.startswith(".cache/") for path in hashed_files)


def test_missing_local_models_explain_how_to_download(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="models download"):
        models.require_model_paths(tmp_path)
