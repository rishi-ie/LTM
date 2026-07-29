"""Tokenizer-offset-based deterministic chunking."""

import hashlib
from typing import Any, Iterable

from ltm_poc.config import WorkspaceConfig
from ltm_poc.schemas import ChunkRecord, TextRecord


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def chunk_records(
    records: Iterable[TextRecord], tokenizer: Any, config: WorkspaceConfig
) -> list[ChunkRecord]:
    """Split records using the frozen embedding tokenizer's exact offsets."""
    chunks: list[ChunkRecord] = []
    step = config.chunk_wordpieces - config.chunk_overlap_wordpieces
    for record in records:
        encoded = tokenizer(
            record.text,
            add_special_tokens=False,
            return_offsets_mapping=True,
            truncation=False,
        )
        pairs = [
            (token_id, offset)
            for token_id, offset in zip(encoded["input_ids"], encoded["offset_mapping"])
            if offset[1] > offset[0]
        ]
        for window_index, token_start in enumerate(range(0, len(pairs), step)):
            window = pairs[token_start : token_start + config.chunk_wordpieces]
            if not window:
                continue
            char_start = window[0][1][0]
            char_end = window[-1][1][1]
            text = record.text[char_start:char_end]
            retokenized = tokenizer(text, add_special_tokens=False, truncation=False)[
                "input_ids"
            ]
            if len(retokenized) > config.chunk_wordpieces:
                raise ValueError("tokenizer offsets produced an oversized chunk")
            token_end = token_start + len(window)
            chunks.append(
                ChunkRecord(
                    chunk_id=f"{record.record_id}::chunk-{window_index:06d}",
                    record_id=record.record_id,
                    source_path=record.source_path,
                    source_kind=record.source_kind,
                    text=text,
                    char_start=char_start,
                    char_end=char_end,
                    token_start=token_start,
                    token_end=token_end,
                    token_count=len(window),
                    content_hash=_hash_text(text),
                    metadata=record.metadata,
                )
            )
    return chunks
