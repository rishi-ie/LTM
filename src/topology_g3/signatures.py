"""Supplementary controlled prompt parser for G3-Text."""
from __future__ import annotations

from .generator import _norm
from .schemas import PromptMention, PromptSignature


def parse_controlled(record: dict) -> PromptSignature:
    """Text-only parser: it may not read the evaluator-provided core signature."""
    text = record["text"]
    prefix, suffix = "What applies to ", "?"
    if not text.startswith(prefix) or not text.endswith(suffix):
        return PromptSignature(record["prompt_id"], "question", (), (), (), (), (), None, None, "unknown", "asserted", (), "abstain")
    mention_text = text[len(prefix):-len(suffix)]
    parsed = PromptMention(mention_text, _norm(mention_text), "entity", len(prefix), len(prefix) + len(mention_text))
    return PromptSignature(record["prompt_id"], "question", (parsed,), (), (), (), (), None, None, "positive", "asserted", (), "clarify")
