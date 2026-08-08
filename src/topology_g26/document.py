"""Atomic document composition after sentence-level validation."""

from __future__ import annotations

from .schemas import DocumentCompilation, IdentityDecision, SentenceCompilation


def compose_document(document_id: str, sentences: tuple[SentenceCompilation, ...], identities: tuple[IdentityDecision, ...] = ()) -> DocumentCompilation:
    if any(sentence.disposition != "accept" for sentence in sentences):
        return DocumentCompilation(document_id, sentences, identities, None, "clarification_required")
    return DocumentCompilation(document_id, sentences, identities, None, "accept")

