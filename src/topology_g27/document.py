"""Atomic document composition over validated sentence programs."""

from __future__ import annotations

from .identity import PersistentAtomBank
from .schemas import DocumentCompilation, IdentityDecision, SentenceCompilation


def compose(document_id: str, sentences: tuple[SentenceCompilation, ...], session_id: str | None, bank: PersistentAtomBank) -> DocumentCompilation:
    identities: list[IdentityDecision] = []
    for sentence in sentences:
        if sentence.state is None:
            return DocumentCompilation(document_id, sentences, (), None, "clarification_required")
        for atom in sentence.state.atoms:
            identities.append(bank.resolve(type("Atom", (), {"atom_id": atom.atom_id, "canonical_text": atom.text, "kind": atom.node_kind, "context": type("Context", (), {"scope_id": "global"})()})(), session_id))
    if any(sentence.disposition != "accept" for sentence in sentences):
        return DocumentCompilation(document_id, sentences, tuple(identities), None, "clarification_required")
    programs = [sentence.field_program for sentence in sentences if sentence.field_program is not None]
    return DocumentCompilation(document_id, sentences, tuple(identities), programs[0] if programs else None, "accept")
