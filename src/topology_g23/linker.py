"""Bounded typed cross-sentence linking over public topology candidates."""

from __future__ import annotations

import torch

from .registry import RELATION_LABELS
from .schemas import CrossSentenceLink, PublicTopologyCandidate, SentenceSource, TypedSpanCandidate

NONE_INDEX = len(RELATION_LABELS)


def candidate_text(source: SentenceSource, span: TypedSpanCandidate, candidate: PublicTopologyCandidate) -> str:
    aliases = " | ".join(candidate.aliases)
    return (
        f"[SOURCE_KIND={span.node_kind}] [SOURCE_SPAN={span.text}] "
        f"[OBJECT_KIND={candidate.object_kind}] [OBJECT={candidate.canonical_text}] "
        f"[ALIASES={aliases}] [SCOPE={candidate.scope_id}]"
    )


def _compatible(source: SentenceSource, candidate: PublicTopologyCandidate) -> bool:
    return candidate.session_id in {None, source.session_id}


def link_candidates(model, source: SentenceSource, spans: tuple[TypedSpanCandidate, ...], candidates: tuple[PublicTopologyCandidate, ...], confidence: float = .70, margin: float = .05) -> tuple[CrossSentenceLink, ...]:
    if not spans:
        return ()
    public = tuple(candidate for candidate in candidates if _compatible(source, candidate))
    if not public:
        return ()
    # One source sentence may expose several spans; link only the highest
    # confidence span in this bounded first version and retain no-link on doubt.
    span = max(spans, key=lambda value: (value.span_probability, value.kind_probability, value.candidate_id))
    logits = model.link_logits([source.text] * len(public), [candidate_text(source, span, candidate) for candidate in public])
    probabilities = torch.softmax(logits, -1)
    flattened: list[tuple[float, int, int]] = []
    for candidate_index in range(len(public)):
        for relation_index in range(len(RELATION_LABELS)):
            flattened.append((float(probabilities[candidate_index, relation_index]), candidate_index, relation_index))
    flattened.sort(key=lambda row: (-row[0], public[row[1]].object_id, RELATION_LABELS[row[2]]))
    best_probability, best_candidate, best_relation = flattened[0]
    next_probability = flattened[1][0] if len(flattened) > 1 else 0.0
    no_link = float(probabilities[:, NONE_INDEX].max())
    margin_value = best_probability - max(next_probability, no_link)
    if best_probability < confidence or margin_value < margin:
        return ()
    relation = RELATION_LABELS[best_relation]
    return (
        CrossSentenceLink(
            relation,
            span.candidate_id,
            public[best_candidate].object_id,
            (),
            best_probability,
            margin_value,
        ),
    )
