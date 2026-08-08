"""Shared MiniLM projection and optional learned L5 compatibility gate."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.nn import functional as f


class EquilibriumKernel(nn.Module):
    """One small kernel shared by compiler coordinates and body compatibility."""

    def __init__(self, semantic_dimension: int = 384, state_dimension: int = 128) -> None:
        super().__init__()
        self.projection = nn.Linear(semantic_dimension, state_dimension, bias=False)
        self.gate = nn.Sequential(
            nn.Linear(state_dimension * 3, 128),
            nn.Tanh(),
            nn.Linear(128, 1),
        )

    def project(self, values: torch.Tensor) -> torch.Tensor:
        return f.normalize(self.projection(values), dim=-1)

    def compatibility(
        self,
        state: torch.Tensor,
        source: torch.Tensor,
        outcome: torch.Tensor,
    ) -> torch.Tensor:
        return torch.sigmoid(self.gate(torch.cat((state, source, outcome), dim=-1))).squeeze(-1)


def parameter_count(model: nn.Module) -> int:
    return sum(item.numel() for item in model.parameters())


class MiniLMCoordinateEncoder:
    """Local-only MiniLM followed by the frozen L5 shared projection."""

    def __init__(self, model_path: Path, kernel: EquilibriumKernel) -> None:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(
            str(model_path), local_files_only=True, device="cpu"
        )
        self.kernel = kernel.eval()
        self.forward_calls = 0

    def encode(self, source_id: str, text: str) -> tuple[float, ...]:
        del source_id
        self.forward_calls += 1
        row = self.model.encode(
            [text],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )[0].astype(np.float32)
        with torch.no_grad():
            projected = self.kernel.project(torch.from_numpy(row).reshape(1, -1))[0]
        return tuple(float(item) for item in projected.tolist())


class CachedCoordinateEncoder:
    """Projection boundary for already encoded MiniLM rows."""

    def __init__(self, rows: dict[str, np.ndarray], kernel: EquilibriumKernel) -> None:
        self.rows = rows
        self.kernel = kernel.eval()
        self.forward_calls = 0

    def encode(self, source_id: str, text: str) -> tuple[float, ...]:
        del text
        self.forward_calls += 1
        value = np.asarray(self.rows[source_id], dtype=np.float32)
        with torch.no_grad():
            projected = self.kernel.project(torch.from_numpy(value).reshape(1, -1))[0]
        return tuple(float(item) for item in projected.tolist())


def train_kernel(
    semantic_rows: np.ndarray,
    positive_pairs: np.ndarray,
    negative_pairs: np.ndarray,
    body_triples: np.ndarray,
    *,
    steps: int,
    batch_size: int,
    seed: int,
) -> tuple[EquilibriumKernel, tuple[float, ...]]:
    """Train alignment and a local gate without route or answer supervision."""

    torch.manual_seed(seed)
    torch.set_num_threads(4)
    model = EquilibriumKernel(semantic_rows.shape[1])
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=0.01)
    rows = torch.from_numpy(np.asarray(semantic_rows, dtype=np.float32))
    positives = np.asarray(positive_pairs, dtype=np.int64)
    negatives = np.asarray(negative_pairs, dtype=np.int64)
    triples = np.asarray(body_triples, dtype=np.int64)
    rng = np.random.default_rng(seed)
    losses: list[float] = []
    for _ in range(steps):
        pair_ids = rng.choice(
            len(positives), size=min(batch_size, len(positives)), replace=False
        )
        body_ids = rng.choice(
            len(triples), size=min(batch_size, len(triples)), replace=False
        )
        positive = positives[pair_ids]
        # Each negative belongs to the same prompt as its positive pair.  The
        # previous independent sampling compared unrelated prompt pairs and
        # weakened the actual source/prompt retrieval objective.
        negative = negatives[pair_ids]
        body = triples[body_ids]
        projected = model.project(rows)
        prompt_rows = projected[positive[:, 0]]
        relevant_rows = projected[positive[:, 1]]
        positive_similarity = (prompt_rows * relevant_rows).sum(-1)
        negative_similarity = (
            projected[negative[:, 0]] * projected[negative[:, 1]]
        ).sum(-1)
        paired_margin = f.relu(
            0.35 - positive_similarity + negative_similarity
        ).mean()
        # In-batch contrast makes recall@k the trained objective rather than an
        # accidental consequence of a single random-negative margin.
        logits = prompt_rows @ relevant_rows.T / 0.07
        labels = torch.arange(len(pair_ids), device=logits.device)
        contrastive = 0.5 * (
            f.cross_entropy(logits, labels)
            + f.cross_entropy(logits.T, labels)
        )
        alignment = 0.5 * (paired_margin + contrastive)
        state = projected[body[:, 0]]
        relevant = projected[body[:, 1]]
        unrelated = projected[body[:, 2]]
        # Match the runtime callback exactly: (current state, body input,
        # body output).  A compiled body currently has one shared coordinate
        # for its exact input/outcome occurrences, so both body arguments use
        # the relevant (or unrelated) body coordinate during this curriculum.
        positive_gate = model.compatibility(
            state.detach(), relevant.detach(), relevant.detach()
        )
        negative_gate = model.compatibility(
            state.detach(), unrelated.detach(), unrelated.detach()
        )
        gating = f.relu(0.35 - positive_gate + negative_gate).mean()
        loss = alignment + gating
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        losses.append(float(loss.detach()))
    return model.eval(), tuple(losses)


def save_kernel(path: Path, model: EquilibriumKernel, losses: tuple[float, ...], seed: int) -> dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model": model.state_dict(), "losses": losses, "seed": seed}, path)
    return {
        "parameters": parameter_count(model),
        "weight_bytes": sum(item.numel() * item.element_size() for item in model.parameters()),
        "final_loss": losses[-1] if losses else None,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def load_kernel(path: Path) -> EquilibriumKernel:
    payload = torch.load(path, map_location="cpu", weights_only=False)
    model = EquilibriumKernel()
    model.load_state_dict(payload["model"])
    return model.eval()


class NumpyCompatibility:
    """Bounded soft adapter from the learned gate to field influence.

    Exact semantic applicability is established outside the vector layer.  A
    learned similarity score may modulate that source-backed influence, but it
    must not erase an exact body or become a hidden authorization boundary.
    """

    def __init__(
        self,
        kernel: EquilibriumKernel,
        *,
        minimum_multiplier: float = 0.75,
    ) -> None:
        if not 0.0 <= minimum_multiplier <= 1.0:
            raise ValueError("invalid compatibility modulation floor")
        self.kernel = kernel.eval()
        self.minimum_multiplier = float(minimum_multiplier)

    def __call__(self, mode: np.ndarray, source: np.ndarray, outcome: np.ndarray, body: object) -> float:
        del body
        with torch.no_grad():
            value = self.kernel.compatibility(
                torch.from_numpy(np.asarray(mode, dtype=np.float32)).reshape(1, -1),
                torch.from_numpy(np.asarray(source, dtype=np.float32)).reshape(1, -1),
                torch.from_numpy(np.asarray(outcome, dtype=np.float32)).reshape(1, -1),
            )[0]
        return self.minimum_multiplier + (1.0 - self.minimum_multiplier) * float(value)
