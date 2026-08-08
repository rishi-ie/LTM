"""Inference-only sentence compiler. It accepts no evaluator labels or template identifiers."""
from __future__ import annotations

import time

import torch

from .assemble import assemble, render_fragment, round_trip_similarity
from .encoder import RawTokenEncoder
from .hrm import (
    DISPOSITION_LABELS,
    NODE_KINDS,
    ROLE_LABELS,
    SCOPE_LABELS,
    CandidateBatch,
    TypedRecurrentHRM,
)
from .registry import RELATION_LABELS, direction_for, enumerate_legal_candidates
from .schemas import (
    CompilerResult,
    SentenceFragment,
    SentenceSource,
    SpanProposal,
    StructuredRelationCandidate,
    TopologyLinkCandidate,
)


def _softmax_confidence(values: torch.Tensor) -> tuple[float, float]:
    if values.numel() == 0:
        return 0.0, 0.0
    probabilities = torch.softmax(values, 0)
    ordered = torch.topk(probabilities, min(2, probabilities.numel())).values
    confidence = float(ordered[0])
    margin = float(ordered[0] - ordered[1]) if ordered.numel() == 2 else confidence
    return confidence, margin


class SentenceCompiler:
    """Raw-token HRM compiler with a bounded legal-candidate space."""

    def __init__(self, partial_tune: bool = False, recurrent: bool = True) -> None:
        self.encoder = RawTokenEncoder(partial_tune=partial_tune)
        self.hrm = TypedRecurrentHRM(self.encoder.hidden_size, recurrent=recurrent)
        self.encoder.eval(); self.hrm.eval()

    @property
    def modules(self) -> tuple[torch.nn.Module, torch.nn.Module]:
        return self.encoder, self.hrm

    def state_dict(self) -> dict[str, object]:
        return {"encoder": self.encoder.state_dict(), "hrm": self.hrm.state_dict()}

    def load_state_dict(self, state: dict[str, object]) -> None:
        self.encoder.load_state_dict(state["encoder"])
        self.hrm.load_state_dict(state["hrm"])

    def _propose_spans(self, source: SentenceSource, offsets: torch.Tensor, start_logits: torch.Tensor, end_logits: torch.Tensor) -> tuple[SpanProposal, ...]:
        """Multi-kind start/end proposals permit overlapping arguments; capped at twelve."""
        proposals: list[SpanProposal] = []
        starts = torch.softmax(start_logits, -1)[0]
        ends = torch.softmax(end_logits, -1)[0]
        offset_rows = offsets[0].tolist()
        for kind_index, kind in enumerate(NODE_KINDS, start=1):
            # One high-confidence start/end pair per kind plus a runner-up if it is non-overlapping.
            start_ids = torch.topk(starts[:, kind_index], min(3, starts.shape[0])).indices.tolist()
            end_ids = torch.topk(ends[:, kind_index], min(3, ends.shape[0])).indices.tolist()
            for start_id in start_ids:
                valid_end = next((end_id for end_id in end_ids if end_id >= start_id and offset_rows[end_id][1] > offset_rows[start_id][0]), None)
                if valid_end is None:
                    continue
                begin, finish = offset_rows[start_id][0], offset_rows[valid_end][1]
                if finish <= begin:
                    continue
                value = source.text[begin:finish]
                confidence = float((starts[start_id, kind_index] * ends[valid_end, kind_index]).sqrt())
                if any(item.start == begin and item.end == finish and item.node_kind == kind for item in proposals):
                    continue
                proposals.append(SpanProposal(f"s{len(proposals) + 1}", value, kind, begin, finish, confidence))
                if len(proposals) >= 12:
                    return tuple(proposals)
                break
        return tuple(sorted(proposals, key=lambda item: (item.start, item.end, item.node_kind)))

    @staticmethod
    def candidate_batch(spans: tuple[SpanProposal, ...]) -> tuple[CandidateBatch, tuple[tuple[str, tuple[tuple[str, tuple[str, ...]], ...]], ...]]:
        legal = enumerate_legal_candidates(spans, maximum=48)
        span_indices = {span.local_id: index for index, span in enumerate(spans)}
        relation_ids: list[int] = []
        role_ids: list[list[int]] = []
        bound_ids: list[list[int]] = []
        for relation, bindings in legal:
            relation_ids.append(RELATION_LABELS.index(relation))
            role_row: list[int] = []
            bound_row: list[int] = []
            for role, local_ids in bindings:
                role_row.append(ROLE_LABELS.index(role))
                bound_row.extend(span_indices[item] for item in local_ids)
            role_ids.append((role_row + [len(ROLE_LABELS)])[:3])
            bound_ids.append((bound_row + [-1, -1, -1, -1])[:4])
        if not legal:
            empty = torch.empty(0, dtype=torch.long)
            return CandidateBatch(empty, empty.reshape(0, 3), empty.reshape(0, 4), torch.empty(0, dtype=torch.bool)), legal
        return CandidateBatch(
            torch.tensor(relation_ids, dtype=torch.long),
            torch.tensor(role_ids, dtype=torch.long),
            torch.tensor(bound_ids, dtype=torch.long),
            torch.ones(len(legal), dtype=torch.bool),
        ), legal

    def _fragment_from_states(
        self,
        source: SentenceSource,
        offsets: torch.Tensor,
        token_states: torch.Tensor,
        hub: torch.Tensor,
        outputs: dict[str, torch.Tensor],
        confidence_threshold: float,
        margin_threshold: float,
        round_trip_threshold: float,
    ) -> SentenceFragment:
        spans = self._propose_spans(source, offsets, outputs["start"], outputs["end"])
        batch, legal = self.candidate_batch(spans)
        if legal:
            kinds = torch.tensor([[NODE_KINDS.index(span.node_kind) + 1 for span in spans]], dtype=torch.long)
            offset_rows = offsets[0].tolist()
            starts, ends = [], []
            for span in spans:
                start = next((i for i, pair in enumerate(offset_rows) if pair[0] <= span.start < pair[1]), 0)
                end = next((i + 1 for i, pair in reversed(list(enumerate(offset_rows))) if pair[0] < span.end <= pair[1]), start + 1)
                starts.append(start); ends.append(max(start + 1, end))
            span_states = self.hrm.span_states(token_states, torch.tensor([starts]), torch.tensor([ends]), kinds)
            scores = self.hrm.score_candidates(span_states, hub, batch)
            best = int(scores.argmax())
            relation_confidence, relation_margin = _softmax_confidence(scores)
            relation, bindings = legal[best]
        else:
            relation_confidence, relation_margin, relation, bindings = 0.0, 0.0, "", ()
        disposition = DISPOSITION_LABELS[int(outputs["disposition"].argmax(-1)[0])]
        scope = SCOPE_LABELS[int(outputs["scope"].argmax(-1)[0])]
        if not legal or disposition != "accept" or relation_confidence < confidence_threshold or relation_margin < margin_threshold:
            final_disposition = "clarification_required" if disposition == "clarification_required" else "quarantine"
            return SentenceFragment(source, final_disposition, (), (), "low_confidence" if final_disposition == "clarification_required" else None, "low_confidence" if final_disposition == "quarantine" else None, None, 0.0)
        else:
            candidate = StructuredRelationCandidate(relation, bindings, direction_for(relation), scope, None, None, relation_confidence, relation_margin)
            provisional = SentenceFragment(source, "accept", spans, (candidate,), None, None, None, 0.0)
            rendered = render_fragment(provisional)
            similarity = round_trip_similarity(source.text, rendered)
            if similarity < round_trip_threshold:
                return SentenceFragment(source, "clarification_required", (), (), "round_trip_low", None, rendered, similarity)
            return SentenceFragment(source, "accept", spans, (candidate,), None, None, rendered, similarity)

    def compile_many(
        self,
        sources: tuple[SentenceSource, ...],
        confidence_threshold: float = 0.85,
        margin_threshold: float = 0.20,
        round_trip_threshold: float = 0.85,
        batch_size: int = 16,
    ) -> tuple[CompilerResult, ...]:
        """Compile sources in true token batches while retaining isolated atomic sentence deltas."""
        results: list[CompilerResult] = []
        for first in range(0, len(sources), batch_size):
            group = sources[first:first + batch_size]; started = time.perf_counter()
            encoded = self.encoder.tokenize([source.text for source in group]); offsets = encoded.pop("offset_mapping")
            extra = {key: value for key, value in encoded.items() if key not in {"input_ids", "attention_mask"}}
            with torch.no_grad():
                raw_tokens = self.encoder(encoded["input_ids"], encoded["attention_mask"], **extra)
                token_states, hubs, outputs = self.hrm.token_states(raw_tokens, encoded["attention_mask"])
                fragments = tuple(
                    self._fragment_from_states(
                        source,
                        offsets[index:index + 1],
                        token_states[index:index + 1],
                        hubs[index:index + 1],
                        {key: value[index:index + 1] for key, value in outputs.items()},
                        confidence_threshold,
                        margin_threshold,
                        round_trip_threshold,
                    )
                    for index, source in enumerate(group)
                )
            elapsed = (time.perf_counter() - started) * 1000 / len(group)
            for index, fragment in enumerate(fragments):
                assembled = assemble(fragment)
                results.append(CompilerResult(
                    group[index].source_id, fragment, (), assembled.delta if assembled else None,
                    assembled.handoff if assembled else None, fragment.disposition, elapsed,
                    int(encoded["attention_mask"][index].sum()),
                ))
        return tuple(results)

    def compile(self, source: SentenceSource, confidence_threshold: float = 0.85, margin_threshold: float = 0.20, round_trip_threshold: float = 0.85) -> CompilerResult:
        return self.compile_many((source,), confidence_threshold, margin_threshold, round_trip_threshold, 1)[0]

    def link(
        self,
        source: SentenceSource,
        spans: tuple[SpanProposal, ...],
        public_candidates: tuple[tuple[str, str, str, str | None], ...],
        confidence_threshold: float = 0.85,
        margin_threshold: float = 0.20,
    ) -> tuple[TopologyLinkCandidate, ...]:
        return self.link_many(((source, spans, public_candidates),), confidence_threshold, margin_threshold, 1)[0]

    def link_many(
        self,
        requests: tuple[tuple[SentenceSource, tuple[SpanProposal, ...], tuple[tuple[str, str, str, str | None], ...]], ...],
        confidence_threshold: float = 0.85,
        margin_threshold: float = 0.20,
        batch_size: int = 8,
    ) -> tuple[tuple[TopologyLinkCandidate, ...], ...]:
        """Batched sparse linker. Each request materializes at most sixteen public candidates."""
        resolved: list[tuple[TopologyLinkCandidate, ...]] = [() for _ in requests]
        active = [(index, source, spans, tuple(item for item in public if item[3] in {None, source.session_id})[:16]) for index, (source, spans, public) in enumerate(requests) if spans]
        active = [item for item in active if item[3]]
        for first in range(0, len(active), batch_size):
            group = active[first:first + batch_size]
            encoded = self.encoder.tokenize([item[1].text for item in group]); encoded.pop("offset_mapping")
            extra = {key: value for key, value in encoded.items() if key not in {"input_ids", "attention_mask"}}
            flattened = [candidate[1] for _index, _source, _spans, candidates in group for candidate in candidates]
            target = self.encoder.tokenize(flattened); target.pop("offset_mapping")
            target_extra = {key: value for key, value in target.items() if key not in {"input_ids", "attention_mask"}}
            with torch.no_grad():
                source_tokens = self.encoder(encoded["input_ids"], encoded["attention_mask"], **extra)
                _states, hubs, output = self.hrm.token_states(source_tokens, encoded["attention_mask"])
                target_tokens = self.encoder(target["input_ids"], target["attention_mask"], **target_extra)
                target_states = self.hrm.masked_mean(self.hrm.token_projection(target_tokens), target["attention_mask"])
                offset = 0
                for local_index, (request_index, source, spans, candidates) in enumerate(group):
                    width = len(candidates); candidate_states = target_states[offset:offset + width]; offset += width
                    relation_id = int(output["link_type"].argmax(-1)[local_index])
                    scores = self.hrm.score_links(hubs[local_index:local_index + 1], candidate_states, torch.full((width,), relation_id, dtype=torch.long))
                    confidence, margin = _softmax_confidence(scores)
                    if confidence >= confidence_threshold and margin >= margin_threshold:
                        object_id, _label, _kind, session = candidates[int(scores.argmax())]
                        resolved[request_index] = (TopologyLinkCandidate(RELATION_LABELS[relation_id], spans[0].local_id, object_id, session, "conversation_local", None, confidence, margin),)
        return tuple(resolved)
