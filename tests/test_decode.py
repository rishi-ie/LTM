"""Decoder cannot emit unsupported claims without selecting fallback."""

from ltm_poc.decode import fallback
from ltm_poc.schemas import EvidenceItem


def test_fallback_preserves_only_evidence() -> None:
    answer = fallback(
        [EvidenceItem(rank=1, chunk_id="c1", source_path="s", score=1, text="fact")],
        "test",
    )
    assert answer.used_fallback
    assert answer.citation_chunk_ids == ["c1"]
    assert "fact" in answer.text
