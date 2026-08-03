from __future__ import annotations

import copy
import random
from dataclasses import dataclass

import numpy as np
import torch
from torch import nn

from .dataset import DIRECTIONS, DISPOSITIONS, LABELS, ROLE_LABELS, SCOPES, ReasoningCase
from .models import MultiHead


@dataclass(frozen=True)
class Labels:
    relation: np.ndarray
    direction: np.ndarray
    roles: np.ndarray
    scope: np.ndarray
    disposition: np.ndarray
    mask: np.ndarray


def set_seed(seed: int = 1729) -> None:
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)


def labels(cases: tuple[ReasoningCase, ...]) -> Labels:
    role_map = {name: i for i, name in enumerate(ROLE_LABELS)}
    array = np.full((len(cases), 3), role_map["pad"], dtype=np.int64)
    mask = np.zeros((len(cases), 3), dtype=np.bool_)
    for i, case in enumerate(cases):
        for slot, role in enumerate(case.gold_roles): array[i, slot] = role_map[role]; mask[i, slot] = True
    return Labels(np.array([LABELS.index(c.gold_relation) for c in cases]), np.array([DIRECTIONS.index(c.gold_direction) for c in cases]), array, np.array([SCOPES.index(c.gold_scope) for c in cases]), np.array([DISPOSITIONS.index(c.gold_disposition) for c in cases]), mask)


def _loss(outputs: dict[str, torch.Tensor], target: Labels, indices: np.ndarray) -> torch.Tensor:
    ce = nn.CrossEntropyLoss()
    rel = torch.as_tensor(target.relation[indices]); direction = torch.as_tensor(target.direction[indices]); scope = torch.as_tensor(target.scope[indices]); disposition = torch.as_tensor(target.disposition[indices]); roles = torch.as_tensor(target.roles[indices]); mask = torch.as_tensor(target.mask[indices])
    role_loss = sum(ce(outputs["roles"][:, slot][mask[:, slot]], roles[:, slot][mask[:, slot]]) for slot in range(3) if bool(mask[:, slot].any())) / max(1, int(mask.any(dim=0).sum()))
    return ce(outputs["relation"], rel) + .5 * ce(outputs["direction"], direction) + .5 * role_loss + .25 * ce(outputs["scope"], scope) + .25 * ce(outputs["disposition"], disposition)


def train_model(train_x: np.ndarray, train_cases: tuple[ReasoningCase, ...], dev_x: np.ndarray, dev_cases: tuple[ReasoningCase, ...], nonlinear: bool, learning_rate: float, weight_decay: float, epochs: int = 100) -> tuple[MultiHead, dict]:
    set_seed()
    model = MultiHead(train_x.shape[1], len(ROLE_LABELS), nonlinear)
    optim = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
    train_y, dev_y = labels(train_cases), labels(dev_cases)
    best_state, best_loss, stale = None, float("inf"), 0
    order = np.arange(len(train_x))
    for epoch in range(epochs):
        np.random.default_rng(1729 + epoch).shuffle(order)
        model.train()
        for start in range(0, len(order), 128):
            indices = order[start:start + 128]
            out = model(torch.as_tensor(train_x[indices]))
            loss = _loss(out, train_y, indices)
            optim.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); optim.step()
        model.eval()
        with torch.no_grad(): value = float(_loss(model(torch.as_tensor(dev_x)), dev_y, np.arange(len(dev_x))))
        if value < best_loss - 1e-7:
            best_loss, stale, best_state = value, 0, copy.deepcopy(model.state_dict())
        else:
            stale += 1
            if stale >= 15: break
    assert best_state is not None
    model.load_state_dict(best_state)
    return model, {"epochs": epoch + 1, "validation_loss": best_loss, "learning_rate": learning_rate, "weight_decay": weight_decay, "nonlinear": nonlinear}


def predict(model: MultiHead, x: np.ndarray) -> dict[str, np.ndarray]:
    model.eval()
    with torch.no_grad(): out = model(torch.as_tensor(x))
    return {key: value.cpu().numpy() for key, value in out.items()}
