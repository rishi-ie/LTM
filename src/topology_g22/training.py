"""Deterministic CPU training for frozen and partial-token encoder G2.2 candidates."""
from __future__ import annotations

import copy
import random
from dataclasses import dataclass
from typing import TypeVar

import numpy as np
import torch
from torch import nn

from .compiler import SentenceCompiler
from .dataset import LinkExample, SentenceExample
from .hrm import DISPOSITION_LABELS, NODE_KINDS, ROLE_LABELS, SCOPE_LABELS, CandidateBatch
from .registry import RELATION_LABELS, enumerate_legal_candidates

T = TypeVar("T")


def _cache_texts(
    sentence_train: tuple[SentenceExample, ...],
    sentence_development: tuple[SentenceExample, ...],
    link_train: tuple[LinkExample, ...],
    link_development: tuple[LinkExample, ...],
) -> tuple[str, ...]:
    values: set[str] = set()
    for example in (*sentence_train, *sentence_development, *link_train, *link_development):
        values.add(example.source.text)
        if isinstance(example, LinkExample):
            values.update(candidate[1] for candidate in example.public_candidates)
    return tuple(sorted(values))


@dataclass(frozen=True, slots=True)
class TrainingInfo:
    variant: str
    recurrent: bool
    partial_tune: bool
    epochs: int
    best_development_loss: float
    hrm_learning_rate: float
    encoder_learning_rate: float | None


def set_seed(seed: int = 1742) -> None:
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)


def build_frozen_state_cache(compiler: SentenceCompiler, texts: tuple[str, ...], batch_size: int = 64) -> dict[str, torch.Tensor]:
    """Compute raw token states once and keep half-precision CPU copies under the 20 GB envelope."""
    cache: dict[str, torch.Tensor] = {}
    compiler.encoder.eval()
    for start in range(0, len(texts), batch_size):
        group = texts[start:start + batch_size]
        encoded = compiler.encoder.tokenize(list(group)); encoded.pop("offset_mapping")
        extra = {key: value for key, value in encoded.items() if key not in {"input_ids", "attention_mask"}}
        with torch.no_grad():
            states = compiler.encoder(encoded["input_ids"], encoded["attention_mask"], **extra).cpu()
        for index, text in enumerate(group):
            length = int(encoded["attention_mask"][index].sum())
            cache[text] = states[index, :length].to(torch.float16).contiguous()
    return cache


def _cached_encoder_batch(compiler: SentenceCompiler, texts: list[str], cache: dict[str, torch.Tensor]) -> tuple[dict[str, torch.Tensor], torch.Tensor]:
    encoded = compiler.encoder.tokenize(texts)
    width = encoded["input_ids"].shape[1]
    states = torch.zeros((len(texts), width, compiler.encoder.hidden_size), dtype=torch.float32)
    for index, text in enumerate(texts):
        cached = cache[text].float()
        states[index, :min(width, cached.shape[0])] = cached[:width]
    return encoded, states


def _token_index(offsets: torch.Tensor, start: int, end: int) -> tuple[int, int] | None:
    rows = offsets[0].tolist()
    valid = [index for index, (left, right) in enumerate(rows) if right > left]
    begin = next((index for index in valid if rows[index][0] <= start < rows[index][1] or rows[index][0] == start), None)
    finish = next((index for index in reversed(valid) if rows[index][0] < end <= rows[index][1] or rows[index][1] == end), None)
    return (begin, finish + 1) if begin is not None and finish is not None and finish >= begin else None


def _sentence_targets(example: SentenceExample, offsets: torch.Tensor, attention_mask: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    length = offsets.shape[1]
    start = torch.full((length,), -100, dtype=torch.long)
    end = torch.full((length,), -100, dtype=torch.long)
    usable = (offsets[0, :, 1] > offsets[0, :, 0]) & attention_mask[0].bool()
    start[usable] = 0; end[usable] = 0
    span_starts: list[int] = []; span_ends: list[int] = []; kinds: list[int] = []
    for span in example.gold.spans:
        token_range = _token_index(offsets, span.start, span.end)
        if token_range is None:
            continue
        left, right = token_range; kind = NODE_KINDS.index(span.node_kind) + 1
        start[left] = kind; end[right - 1] = kind
        span_starts.append(left); span_ends.append(right); kinds.append(kind)
    if not span_starts:
        span_starts, span_ends, kinds = [0], [1], [0]
    return start, end, torch.tensor([span_starts]), torch.tensor([span_ends]), torch.tensor([kinds])


def _gold_candidate_batch(example: SentenceExample) -> tuple[CandidateBatch, int]:
    if not example.gold.relations:
        empty = torch.empty(0, dtype=torch.long)
        return CandidateBatch(empty, empty.reshape(0, 3), empty.reshape(0, 4), torch.empty(0, dtype=torch.bool)), -1
    gold = example.gold.relations[0]
    gold_key = (gold.relation_type, gold.role_local_ids)
    legal = (gold_key,) + tuple(item for item in enumerate_legal_candidates(example.gold.spans, 47) if item != gold_key)
    indices = {span.local_id: index for index, span in enumerate(example.gold.spans)}
    relations: list[int] = []; roles: list[list[int]] = []; spans: list[list[int]] = []
    for relation, bindings in legal:
        relations.append(RELATION_LABELS.index(relation))
        role_row: list[int] = []; span_row: list[int] = []
        for role, local_ids in bindings:
            role_row.append(ROLE_LABELS.index(role)); span_row.extend(indices[local] for local in local_ids)
        roles.append((role_row + [len(ROLE_LABELS)])[:3]); spans.append((span_row + [-1, -1, -1, -1])[:4])
    return CandidateBatch(torch.tensor(relations), torch.tensor(roles), torch.tensor(spans), torch.ones(len(relations), dtype=torch.bool)), 0


def _forward_sentence(compiler: SentenceCompiler, example: SentenceExample) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    encoded = compiler.encoder.tokenize([example.source.text]); offsets = encoded.pop("offset_mapping")
    extra = {key: value for key, value in encoded.items() if key not in {"input_ids", "attention_mask"}}
    token_states = compiler.encoder(encoded["input_ids"], encoded["attention_mask"], **extra)
    states, hub, output = compiler.hrm.token_states(token_states, encoded["attention_mask"])
    start_target, end_target, starts, ends, kinds = _sentence_targets(example, offsets, encoded["attention_mask"])
    span_states = compiler.hrm.span_states(states, starts, ends, kinds)
    candidate, gold_index = _gold_candidate_batch(example)
    losses: dict[str, torch.Tensor] = {}
    ce = nn.CrossEntropyLoss(ignore_index=-100)
    losses["span"] = ce(output["start"][0], start_target) + ce(output["end"][0], end_target)
    scope = example.gold.relations[0].scope_id if example.gold.relations else "global"
    losses["metadata"] = 0.25 * nn.CrossEntropyLoss()(output["scope"], torch.tensor([SCOPE_LABELS.index(scope)]))
    losses["disposition"] = 0.25 * nn.CrossEntropyLoss()(output["disposition"], torch.tensor([DISPOSITION_LABELS.index(example.gold.disposition)]))
    if gold_index >= 0:
        scores = compiler.hrm.score_candidates(span_states, hub, candidate)
        losses["candidate"] = nn.CrossEntropyLoss()(scores.unsqueeze(0), torch.tensor([gold_index]))
        # A margin loss uses the first generated legal counterfactual as a hard negative when present.
        losses["counterfactual"] = torch.relu(0.25 - (scores[0] - scores[1])) if scores.numel() > 1 else scores.sum() * 0
    else:
        losses["candidate"] = token_states.sum() * 0; losses["counterfactual"] = token_states.sum() * 0
    total = losses["span"] + losses["metadata"] + losses["disposition"] + losses["candidate"] + losses["counterfactual"]
    return total, losses


def _encoder_forward(compiler: SentenceCompiler, encoded: dict[str, torch.Tensor]) -> torch.Tensor:
    extra = {key: value for key, value in encoded.items() if key not in {"input_ids", "attention_mask"}}
    if not any(parameter.requires_grad for parameter in compiler.encoder.parameters()):
        with torch.no_grad():
            return compiler.encoder(encoded["input_ids"], encoded["attention_mask"], **extra)
    return compiler.encoder(encoded["input_ids"], encoded["attention_mask"], **extra)


def _sentence_batch_loss(compiler: SentenceCompiler, examples: list[SentenceExample], cache: dict[str, torch.Tensor] | None = None) -> torch.Tensor:
    """One MiniLM pass for a configured sixteen-sentence batch; relation scoring stays typed per item."""
    if cache is None:
        encoded = compiler.encoder.tokenize([example.source.text for example in examples])
        offsets = encoded.pop("offset_mapping")
        token_states = _encoder_forward(compiler, encoded)
    else:
        encoded, token_states = _cached_encoder_batch(compiler, [example.source.text for example in examples], cache)
        offsets = encoded.pop("offset_mapping")
    states, hubs, output = compiler.hrm.token_states(token_states, encoded["attention_mask"])
    losses: list[torch.Tensor] = []
    ce = nn.CrossEntropyLoss(ignore_index=-100)
    for index, example in enumerate(examples):
        start_target, end_target, starts, ends, kinds = _sentence_targets(example, offsets[index:index + 1], encoded["attention_mask"][index:index + 1])
        span_states = compiler.hrm.span_states(states[index:index + 1], starts, ends, kinds)
        candidate, gold_index = _gold_candidate_batch(example)
        item_loss = ce(output["start"][index], start_target) + ce(output["end"][index], end_target)
        scope = example.gold.relations[0].scope_id if example.gold.relations else "global"
        item_loss = item_loss + .25 * nn.CrossEntropyLoss()(output["scope"][index:index + 1], torch.tensor([SCOPE_LABELS.index(scope)]))
        item_loss = item_loss + .25 * nn.CrossEntropyLoss()(output["disposition"][index:index + 1], torch.tensor([DISPOSITION_LABELS.index(example.gold.disposition)]))
        if gold_index >= 0:
            scores = compiler.hrm.score_candidates(span_states, hubs[index:index + 1], candidate)
            item_loss = item_loss + nn.CrossEntropyLoss()(scores.unsqueeze(0), torch.tensor([gold_index]))
            if scores.numel() > 1:
                item_loss = item_loss + torch.relu(.25 - (scores[0] - scores[1]))
        losses.append(item_loss)
    return torch.stack(losses).mean()


def _link_loss(compiler: SentenceCompiler, example: LinkExample) -> torch.Tensor:
    """Sparse link selection over public candidates only; no topology scan is represented."""
    if not example.gold.links:
        return next(compiler.hrm.parameters()).sum() * 0
    link = example.gold.links[0]
    encoded = compiler.encoder.tokenize([example.source.text]); encoded.pop("offset_mapping")
    extra = {key: value for key, value in encoded.items() if key not in {"input_ids", "attention_mask"}}
    source_tokens = compiler.encoder(encoded["input_ids"], encoded["attention_mask"], **extra)
    _source_states, hub, output = compiler.hrm.token_states(source_tokens, encoded["attention_mask"])
    target_texts = [item[1] for item in example.public_candidates]
    target = compiler.encoder.tokenize(target_texts); target.pop("offset_mapping")
    target_extra = {key: value for key, value in target.items() if key not in {"input_ids", "attention_mask"}}
    target_states = compiler.encoder(target["input_ids"], target["attention_mask"], **target_extra)
    target_states = compiler.hrm.masked_mean(compiler.hrm.token_projection(target_states), target["attention_mask"])
    source_state = hub[0:1]
    type_id = torch.tensor([RELATION_LABELS.index(link.link_type)] * len(target_texts))
    scores = compiler.hrm.score_links(source_state, target_states, type_id)
    target_index = next(index for index, item in enumerate(example.public_candidates) if item[0] == link.target_object_id)
    type_loss = nn.CrossEntropyLoss()(output["link_type"], torch.tensor([RELATION_LABELS.index(link.link_type)]))
    return nn.CrossEntropyLoss()(scores.unsqueeze(0), torch.tensor([target_index])) + 0.25 * type_loss


def _link_batch_loss(compiler: SentenceCompiler, examples: list[LinkExample], cache: dict[str, torch.Tensor] | None = None) -> torch.Tensor:
    """One source and one flattened target encoder pass for an eight-link batch."""
    active = [example for example in examples if example.gold.links]
    if not active:
        return next(compiler.hrm.parameters()).sum() * 0
    if cache is None:
        encoded = compiler.encoder.tokenize([example.source.text for example in active]); encoded.pop("offset_mapping")
        source_tokens = _encoder_forward(compiler, encoded)
    else:
        encoded, source_tokens = _cached_encoder_batch(compiler, [example.source.text for example in active], cache)
        encoded.pop("offset_mapping")
    _source_states, hubs, output = compiler.hrm.token_states(source_tokens, encoded["attention_mask"])
    flattened = [candidate[1] for example in active for candidate in example.public_candidates]
    if cache is None:
        target = compiler.encoder.tokenize(flattened); target.pop("offset_mapping")
        target_tokens = _encoder_forward(compiler, target)
    else:
        target, target_tokens = _cached_encoder_batch(compiler, flattened, cache)
        target.pop("offset_mapping")
    targets = compiler.hrm.masked_mean(compiler.hrm.token_projection(target_tokens), target["attention_mask"])
    losses: list[torch.Tensor] = []; offset = 0
    for index, example in enumerate(active):
        link = example.gold.links[0]; width = len(example.public_candidates)
        candidate_states = targets[offset:offset + width]; offset += width
        type_id = torch.tensor([RELATION_LABELS.index(link.link_type)] * width)
        scores = compiler.hrm.score_links(hubs[index:index + 1], candidate_states, type_id)
        target_index = next(i for i, candidate in enumerate(example.public_candidates) if candidate[0] == link.target_object_id)
        relation_loss = nn.CrossEntropyLoss()(scores.unsqueeze(0), torch.tensor([target_index]))
        type_loss = nn.CrossEntropyLoss()(output["link_type"][index:index + 1], torch.tensor([RELATION_LABELS.index(link.link_type)]))
        losses.append(relation_loss + .25 * type_loss)
    return torch.stack(losses).mean()


def _batches(items: list[T], size: int) -> list[list[T]]:
    return [items[index:index + size] for index in range(0, len(items), size)]


def train_variant(
    train_sentences: tuple[SentenceExample, ...],
    development_sentences: tuple[SentenceExample, ...],
    train_links: tuple[LinkExample, ...],
    development_links: tuple[LinkExample, ...],
    *,
    partial_tune: bool,
    recurrent: bool,
    hrm_learning_rate: float,
    encoder_learning_rate: float | None,
    max_epochs: int = 30,
    patience: int = 5,
) -> tuple[SentenceCompiler, TrainingInfo]:
    set_seed()
    compiler = SentenceCompiler(partial_tune=partial_tune, recurrent=recurrent)
    compiler.encoder.train(partial_tune); compiler.hrm.train()
    cache = None if partial_tune else build_frozen_state_cache(
        compiler, _cache_texts(train_sentences, development_sentences, train_links, development_links)
    )
    groups = [{"params": compiler.hrm.parameters(), "lr": hrm_learning_rate}]
    if partial_tune:
        groups.append({"params": [item for item in compiler.encoder.parameters() if item.requires_grad], "lr": encoder_learning_rate})
    optimizer = torch.optim.AdamW(groups, weight_decay=0.01)
    best_state: dict[str, object] | None = None; best_loss = float("inf"); stale = 0
    for epoch in range(max_epochs):
        sentence_items, link_items = list(train_sentences), list(train_links)
        random.Random(1742 + epoch).shuffle(sentence_items)
        random.Random(91729 + epoch).shuffle(link_items)
        optimizer.zero_grad(); accumulated = 0
        for batch in _batches(sentence_items, 16):
            loss = _sentence_batch_loss(compiler, batch, cache)
            (loss / 4).backward(); accumulated += 1
            if accumulated == 4:
                torch.nn.utils.clip_grad_norm_(list(compiler.hrm.parameters()) + [p for p in compiler.encoder.parameters() if p.requires_grad], 1.0)
                optimizer.step(); optimizer.zero_grad(); accumulated = 0
        for batch in _batches(link_items, 8):
            loss = _link_batch_loss(compiler, batch, cache)
            (loss / 4).backward(); accumulated += 1
            if accumulated == 4:
                torch.nn.utils.clip_grad_norm_(list(compiler.hrm.parameters()) + [p for p in compiler.encoder.parameters() if p.requires_grad], 1.0)
                optimizer.step(); optimizer.zero_grad(); accumulated = 0
        if accumulated:
            optimizer.step(); optimizer.zero_grad()
        compiler.encoder.eval(); compiler.hrm.eval()
        with torch.no_grad():
            dev_losses = [_sentence_batch_loss(compiler, batch, cache) for batch in _batches(list(development_sentences), 16)]
            dev_losses.extend(_link_batch_loss(compiler, batch, cache) for batch in _batches(list(development_links), 8))
            value = float(torch.stack(dev_losses).mean())
        variant_label = "partial" if partial_tune else "frozen"
        recurrence_label = "hrm" if recurrent else "nonrecurrent"
        print(f"G2.2 {variant_label}/{recurrence_label} epoch {epoch + 1} validation_loss={value:.5f}", flush=True)
        if value < best_loss - 1e-7:
            best_loss, stale, best_state = value, 0, copy.deepcopy(compiler.state_dict())
        else:
            stale += 1
            if stale >= patience:
                break
        compiler.encoder.train(partial_tune); compiler.hrm.train()
    if best_state is None:
        raise RuntimeError("training failed to produce a checkpoint")
    compiler.load_state_dict(best_state); compiler.encoder.eval(); compiler.hrm.eval()
    return compiler, TrainingInfo(
        "partial" if partial_tune else "frozen", recurrent, partial_tune, epoch + 1, best_loss,
        hrm_learning_rate, encoder_learning_rate,
    )
