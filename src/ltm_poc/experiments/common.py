"""Small deterministic helpers shared by experiment harnesses."""

from ltm_poc.schemas import ChunkRecord


def chunks_from_documents(documents: dict[str, str]) -> list[ChunkRecord]:
    return [
        ChunkRecord(
            chunk_id=doc_id,
            record_id=doc_id,
            source_path=doc_id,
            source_kind="text",
            text=text,
            char_start=0,
            char_end=len(text),
            token_start=0,
            token_end=1,
            token_count=1,
            content_hash=doc_id,
            metadata={},
        )
        for doc_id, text in documents.items()
    ]


def quality(ids: list[str], gold: set[str]) -> tuple[float, float]:
    hits = len(set(ids) & gold)
    return hits / len(gold), hits / len(ids) if ids else 0.0
