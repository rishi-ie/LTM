"""One-pass selectively adapted MiniLM boundary for G2.8."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import torch
from transformers import AutoModel, AutoTokenizer

MODEL_PATH = Path(".models/all-MiniLM-L6-v2")
EXPECTED_HASHES = {
    "config.json": "953f9c0d463486b10a6871cc2fd59f223b2c70184f49815e7efbcab5d8908b41",
    "model.safetensors": "53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db",
    "tokenizer.json": "be50c3628f2bf5bb5e3a7f17b1f74611b2561a3a27eeab05e5aa30f411572037",
}


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def assert_model_hashes(path: Path = MODEL_PATH) -> dict[str, str]:
    found = {name: file_hash(path / name) for name in EXPECTED_HASHES}
    if found != EXPECTED_HASHES:
        raise RuntimeError("G2.8 local MiniLM hash mismatch")
    return found


class AdaptedMiniLM(torch.nn.Module):
    """A local encoder with only the final two transformer layers trainable."""

    def __init__(self, path: Path = MODEL_PATH) -> None:
        super().__init__()
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        self.tokenizer = AutoTokenizer.from_pretrained(str(path), local_files_only=True, use_fast=True)
        self.model = AutoModel.from_pretrained(str(path), local_files_only=True)
        self.forward_calls = 0
        encoder_layers = list(self.model.encoder.layer)
        for layer in encoder_layers[:-2]:
            for parameter in layer.parameters():
                parameter.requires_grad = False
        for layer in encoder_layers[-2:]:
            for parameter in layer.parameters():
                parameter.requires_grad = True
        for parameter in self.model.embeddings.parameters():
            parameter.requires_grad = False
        if getattr(self.model, "pooler", None) is not None:
            for parameter in self.model.pooler.parameters():
                parameter.requires_grad = True

    def tokenize(self, texts: list[str]) -> dict[str, torch.Tensor]:
        return dict(self.tokenizer(texts, padding=True, truncation=True, max_length=128, return_offsets_mapping=True, return_tensors="pt"))

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor, **extra: torch.Tensor) -> torch.Tensor:
        self.forward_calls += 1
        kwargs = {"token_type_ids": extra["token_type_ids"]} if "token_type_ids" in extra else {}
        return self.model(input_ids=input_ids, attention_mask=attention_mask, **kwargs).last_hidden_state

    def frozen_parameters_unchanged(self) -> bool:
        return all(not parameter.requires_grad for layer in list(self.model.encoder.layer)[:-2] for parameter in layer.parameters())
