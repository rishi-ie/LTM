"""Sparse linker from validated sentence fragments to public topology index candidates."""
from __future__ import annotations

from dataclasses import dataclass

from .schemas import SpanProposal, TopologyLinkCandidate


@dataclass(frozen=True, slots=True)
class PublicTopologyIndex:
    """Request-local public candidates; a linker is never given the complete topology."""
    candidates: tuple[tuple[str, str, str, str | None], ...]
    session_id: str | None

    def query(self, text: str, expected_kind: str | None = None, maximum: int = 16) -> tuple[tuple[str, str, str, str | None], ...]:
        tokens = set(text.casefold().split())
        ranked = []
        for candidate in self.candidates:
            object_id, label, kind, session = candidate
            if session is not None and session != self.session_id:
                continue
            if expected_kind is not None and kind != expected_kind:
                continue
            score = len(tokens & set(label.casefold().split()))
            ranked.append((-score, object_id, candidate))
        return tuple(item[2] for item in sorted(ranked)[:maximum])


def deterministic_link(
    span: SpanProposal,
    index: PublicTopologyIndex,
    link_type: str = "refers_to",
    scope_id: str = "conversation_local",
    valid_at: int | None = None,
) -> TopologyLinkCandidate | None:
    candidates = index.query(span.text, maximum=16)
    if not candidates:
        return None
    object_id, _label, _kind, _session = candidates[0]
    margin = 1.0 if len(candidates) == 1 else 0.0
    return TopologyLinkCandidate(link_type, span.local_id, object_id, index.session_id, scope_id, valid_at, 1.0, margin)
