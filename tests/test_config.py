"""Configuration, schema, and device checks that do not load models."""

import json

import pytest
from pydantic import ValidationError

from ltm_poc.config import (
    WorkspaceConfig,
    load_workspace_config,
    write_workspace_config,
)
from ltm_poc.devices import device_report, resolve_device
from ltm_poc.schemas import TextRecord


def valid_config(**changes: object) -> WorkspaceConfig:
    values: dict[str, object] = {
        "embedding_model_path": ".models/embed",
        "embedding_model_id": "embed",
        "embedding_revision": "revision",
        "decoder_model_path": ".models/decode",
        "decoder_model_id": "decode",
        "decoder_revision": "revision",
    }
    values.update(changes)
    return WorkspaceConfig.model_validate(values)


def test_rejects_invalid_budgets_and_missing_model_path() -> None:
    with pytest.raises(ValidationError):
        valid_config(chunk_overlap_wordpieces=128)
    with pytest.raises(ValidationError):
        valid_config(evidence_limit=129)
    with pytest.raises(ValidationError):
        valid_config(embedding_model_path="")


def test_config_round_trips_and_resolves_paths(tmp_path) -> None:
    path = tmp_path / "workspace.json"
    write_workspace_config(path, valid_config())
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["device"] == "auto"
    assert load_workspace_config(path).embedding_model_path == str(
        (tmp_path / ".models/embed").resolve()
    )


def test_auto_device_and_report_are_json_safe() -> None:
    assert resolve_device("auto") in {"cpu", "mps"}
    assert json.loads(json.dumps(device_report()))["field_dtype"] == "float64"


def test_text_record_accepts_canonical_metadata() -> None:
    record = TextRecord(
        record_id="r1",
        source_path="note.txt",
        source_kind="text",
        text="note",
        metadata={"line": 1, "active": True, "missing": None},
        content_hash="hash",
    )
    assert record.metadata["line"] == 1
