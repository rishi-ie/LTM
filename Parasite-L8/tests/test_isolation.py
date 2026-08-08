from __future__ import annotations

import hashlib
from pathlib import Path

from parasite.contracts import IngestRequest

from parasite_l8.runtime import L8Runtime


def test_l8_uses_its_own_state(tmp_path: Path) -> None:
    runtime = L8Runtime.open(tmp_path / "l8")
    payload = {"source_text": "isolated", "atoms": [{"id": "a", "expression": "a", "sort": "Prop"}], "factors": [{"id": "b", "inputs": ["a"], "outcome": "a", "polarity": 1}], "source_class_map": {"s": "support"}}
    request = IngestRequest("t", "r", "s", hashlib.sha256(b"isolated").hexdigest(), "mathematical_reality", payload)
    runtime.ingest(request)
    assert (tmp_path / "l8" / "field" / "catalog.sqlite").exists()
    assert not (Path(__file__).resolve().parents[2] / "Parasite" / "var" / "catalog.sqlite").exists()
