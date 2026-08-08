"""Deterministic sentence splitting and offset-safe normalization."""
from __future__ import annotations

import re
import unicodedata

from .schemas import SentenceSource, text_hash

_SENTENCE = re.compile(r"[^.!?]+[.!?]?", re.UNICODE)


def normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).strip().split())


def split_sentences(document_id: str, text: str, session_id: str | None = None) -> tuple[SentenceSource, ...]:
    result: list[SentenceSource] = []
    for index, match in enumerate(_SENTENCE.finditer(text)):
        raw = match.group()
        leading = len(raw) - len(raw.lstrip())
        sentence = normalize(raw)
        if not sentence:
            continue
        start = match.start() + leading
        end = start + len(raw.strip())
        source_id = f"{document_id}:s{index:04d}"
        result.append(SentenceSource(source_id, document_id, session_id, index, sentence, start, end, text_hash(sentence)))
    return tuple(result)
