from __future__ import annotations

import torch

from .assemble import assemble
from .candidates import candidate_tensors, relation_hypotheses
from .schemas import SentenceCompilationResult, SentenceSource, TopologyHypothesis


def _span_token_range(offsets: torch.Tensor, start: int, end: int) -> tuple[int, int]:
    rows = offsets[0].tolist(); valid = [i for i, (left, right) in enumerate(rows) if right > left]
    begin = next((i for i in valid if rows[i][0] <= start < rows[i][1]), valid[0] if valid else 0)
    finish = next((i for i in reversed(valid) if rows[i][0] < end <= rows[i][1]), begin)
    return begin, max(begin + 1, finish + 1)


def decode_from_spans(
    source: SentenceSource,
    spans,
    offsets: torch.Tensor,
    parser_states: torch.Tensor,
    reasoning_states: torch.Tensor,
    hub: torch.Tensor,
    hierarchy,
    confidence: float = .70,
    margin: float = .05,
) -> SentenceCompilationResult:
    if not spans:
        return SentenceCompilationResult(source.source_id, (), None, "quarantine", ("NO_SPAN_CANDIDATES",), 0.0, parser_states.shape[1])
    starts, ends = zip(*(_span_token_range(offsets, span.start, span.end) for span in spans))
    span_states = []
    for start, end in zip(starts, ends): span_states.append(reasoning_states[0, start:end].mean(0))
    span_states = torch.stack(span_states).unsqueeze(0)
    tensor_pack, legal = candidate_tensors(spans)
    relation_ids, role_ids, bound_ids, _ = tensor_pack
    if not legal:
        return SentenceCompilationResult(source.source_id, (), None, "quarantine", ("NO_LEGAL_CANDIDATES",), 0.0, parser_states.shape[1])
    scores, _ = hierarchy.reconcile(span_states, hub, relation_ids, role_ids, bound_ids)
    probs = torch.sigmoid(scores); ordered = torch.argsort(probs, descending=True).tolist()
    best = int(ordered[0]); second = float(probs[ordered[1]]) if len(ordered) > 1 else 0.0
    confidence_value = float(probs[best]); separation = confidence_value - second
    relation_candidates = relation_hypotheses(spans, scores, legal)
    selected = relation_candidates[0] if relation_candidates else None
    if selected is None or confidence_value < confidence or separation < margin:
        reason = "LOW_GRAPH_CONFIDENCE" if selected else "NO_GRAPH"
        return SentenceCompilationResult(source.source_id, (), None, "clarification_required" if selected else "quarantine", (reason,), 0.0, parser_states.shape[1])
    selected_relations = []
    seen = set()
    for candidate in relation_candidates:
        signature = (candidate.relation_type, candidate.role_candidate_ids, candidate.scope_id)
        if signature in seen or candidate.probability < confidence:
            continue
        selected_relations.append(candidate)
        seen.add(signature)
        if len(selected_relations) == 3:
            break
    selected_ids = {
        item
        for relation in selected_relations
        for _role, ids in relation.role_candidate_ids
        for item in ids
    }
    selected_spans = tuple(span for span in spans if span.candidate_id in selected_ids)
    hypothesis = TopologyHypothesis("graph-0", selected_spans, tuple(selected_relations), "accept", confidence_value, separation)
    assembled = assemble(source, hypothesis)
    if assembled is None:
        return SentenceCompilationResult(source.source_id, (hypothesis,), None, "quarantine", ("G1_ASSEMBLY_REJECTED",), 0.0, parser_states.shape[1])
    return SentenceCompilationResult(source.source_id, (hypothesis,), assembled.ir, "accept", (), 0.0, parser_states.shape[1])


def decode_sentence(source: SentenceSource, offsets: torch.Tensor, parser_states: torch.Tensor, reasoning_states: torch.Tensor, hub: torch.Tensor, parser, hierarchy, confidence: float = .70, margin: float = .05) -> SentenceCompilationResult:
    spans = parser.candidate_lattice(
        source,
        offsets,
        parser_states,
        torch.ones((1, parser_states.shape[1]), dtype=torch.long, device=parser_states.device),
    )
    return decode_from_spans(source, spans, offsets, parser_states, reasoning_states, hub, hierarchy, confidence, margin)
