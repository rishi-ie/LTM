from __future__ import annotations

import time

from .generator import _norm
from .indexes import Indexes
from .schemas import AddressCandidate, AddressResult, PromptMention, PromptSignature


def signature_from_dict(value: dict) -> PromptSignature:
    value = dict(value); value["entity_mentions"] = tuple(PromptMention(**x) for x in value["entity_mentions"]); value["predicate_phrases"] = tuple(value["predicate_phrases"]); value["relation_hints"] = tuple(value["relation_hints"]); value["target_variables"] = tuple(value["target_variables"]); value["scope_hints"] = tuple(value["scope_hints"]); value["conversation_references"] = tuple(value["conversation_references"]); value["valid_between"] = tuple(value["valid_between"]) if value["valid_between"] else None; return PromptSignature(**value)

def resolve(signature: PromptSignature, indexes: Indexes, mode: str = "full") -> AddressResult:
    started = time.perf_counter_ns(); scores: dict[str, float] = {}; channels: dict[str, list[str]] = {}; conflicts: dict[str, list[str]] = {}; visited = 0
    def add(ids: list[str], score: float, channel: str) -> None:
        nonlocal visited
        visited += len(ids)
        for aid in ids: scores[aid] = scores.get(aid, 0.0) + score; channels.setdefault(aid, []).append(channel)
    lexical = mode != "semantic"
    for mention in signature.entity_mentions:
        key = _norm(mention.normalized_text)
        if lexical:
            add(indexes.canonical.get(key, []), 3.0, "canonical"); add(indexes.alias.get(key, []), 2.5, "alias")
        if mode in ("full", "semantic") and not indexes.canonical.get(key) and not indexes.alias.get(key):
            add(indexes.semantic_candidates(mention.text), 0.5, "semantic")
    if lexical:
        for phrase in signature.predicate_phrases: add(indexes.predicate.get(_norm(phrase), []), 2.0, "predicate")
    if not scores: return AddressResult(signature.prompt_id, (), (), (), "unknown", 0.0, ("canonical", "alias", "predicate"), visited, 0, False, (time.perf_counter_ns()-started)//1000)
    compatible: list[tuple[str, float]] = []
    for aid, score in scores.items():
        item = indexes.addresses[aid]; bad = False
        # Predicate registry addresses are global routing metadata, not a scoped
        # claim. They accompany the entity address even for local questions.
        if item.object_kind != "predicate" and signature.scope_hints and item.scope_id not in signature.scope_hints: score -= 4; bad = True
        if item.object_kind != "predicate" and signature.valid_at is not None and ((item.valid_from is not None and signature.valid_at < item.valid_from) or (item.valid_to is not None and signature.valid_at > item.valid_to)): score -= 4; bad = True
        if item.object_kind != "predicate" and signature.conversation_references and item.episode_id not in signature.conversation_references: score -= 4; bad = True
        if bad: conflicts.setdefault(aid, []).append("typed_conflict")
        if not bad: compatible.append((aid, score))
    compatible.sort(key=lambda x: (-x[1], x[0])); candidates = tuple(AddressCandidate(aid, score, tuple(channels[aid]), tuple(channels[aid]), tuple(conflicts.get(aid, ()))) for aid, score in compatible[:24])
    if not candidates: disposition, resolved, ambiguity, confidence = "unknown", (), (), 0.0
    elif len(candidates) > 1 and candidates[0].score - candidates[1].score < 0.75: disposition, resolved, ambiguity, confidence = "clarification_required", (), (tuple(x.address_id for x in candidates),), candidates[0].score
    elif candidates[0].score < 3.0: disposition, resolved, ambiguity, confidence = "unknown", (), (), candidates[0].score
    else: disposition, resolved, ambiguity, confidence = "resolved", (candidates[0].address_id,), (), candidates[0].score
    return AddressResult(signature.prompt_id, candidates, resolved, ambiguity, disposition, confidence, ("canonical", "alias", "predicate", "scope", "temporal", "episode"), visited, len(candidates), False, (time.perf_counter_ns()-started)//1000)
