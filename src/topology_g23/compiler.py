from __future__ import annotations

import time

import torch
from torch import nn

from .decode import decode_sentence
from .encoder import FullTokenEncoder
from .hierarchy import HierarchicalReconciler
from .linker import link_candidates
from .registry import RELATION_LABELS
from .schemas import (
    CrossSentenceLink,
    PublicTopologyCandidate,
    SentenceCompilationResult,
    SentenceSource,
)
from .spans import BiaffineSpanParser


class SentenceTopologyCompiler(nn.Module):
    def __init__(self, recurrent: bool = True) -> None:
        super().__init__()
        self.encoder = FullTokenEncoder()
        self.parser = BiaffineSpanParser(self.encoder.hidden_size)
        self.projection = nn.Linear(self.encoder.hidden_size, 128)
        self.hierarchy = HierarchicalReconciler(recurrent=recurrent)
        self.linker_head = nn.Sequential(
            nn.Linear(self.encoder.hidden_size, 128),
            nn.GELU(),
            nn.LayerNorm(128),
            nn.Linear(128, len(RELATION_LABELS) + 1),
        )
        self.recurrent = recurrent

    def forward(self, sources: tuple[SentenceSource, ...], confidence: float = .70, margin: float = .05) -> tuple[SentenceCompilationResult, ...]:
        encoded = self.encoder.tokenize([source.text for source in sources]); offsets = encoded.pop("offset_mapping")
        extra = {key: value for key, value in encoded.items() if key not in {"input_ids", "attention_mask"}}
        raw = self.encoder(encoded["input_ids"], encoded["attention_mask"], **extra)
        projected = self.projection(raw)
        results = []
        for index, source in enumerate(sources):
            start = time.perf_counter()
            states = projected[index:index + 1]; mask = encoded["attention_mask"][index:index + 1]
            hub = (states * mask.unsqueeze(-1)).sum(1) / mask.sum(1, keepdim=True).clamp_min(1)
            result = decode_sentence(source, offsets[index:index + 1], raw[index:index + 1], states, hub, self.parser, self.hierarchy, confidence, margin)
            results.append(SentenceCompilationResult(result.source_id, result.hypotheses, result.accepted_ir, result.disposition, result.failure_codes, (time.perf_counter() - start) * 1000, result.token_count))
        return tuple(results)

    def compile(self, source: SentenceSource, confidence: float = .70, margin: float = .05) -> SentenceCompilationResult:
        self.eval()
        with torch.no_grad(): return self.forward((source,), confidence, margin)[0]

    def link(self, source: SentenceSource, spans, candidates: tuple[PublicTopologyCandidate, ...], confidence: float = .70, margin: float = .05) -> tuple[CrossSentenceLink, ...]:
        self.eval()
        with torch.no_grad():
            return link_candidates(self, source, spans, candidates, confidence, margin)

    def link_logits(self, source_texts: list[str], candidate_texts: list[str]) -> torch.Tensor:
        """Cross-encode bounded public candidates for typed linking."""
        encoded = self.encoder.tokenize_pairs(source_texts, candidate_texts)
        extra = {key: value for key, value in encoded.items() if key not in {"input_ids", "attention_mask"}}
        states = self.encoder(encoded["input_ids"], encoded["attention_mask"], **extra)
        return self.linker_head(states[:, 0])

    def state_dict_bundle(self) -> dict[str, object]:
        return {"state": self.state_dict(), "recurrent": self.recurrent}
