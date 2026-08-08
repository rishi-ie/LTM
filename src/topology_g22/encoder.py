"""Local-only raw-token MiniLM boundary for G2.2."""
from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass
from pathlib import Path

import torch
from transformers import AutoModel, AutoTokenizer

MODEL_PATH = Path(".models/all-MiniLM-L6-v2")
EXPECTED_HASHES = {
    "config.json": "953f9c0d463486b10a6871cc2fd59f223b2c70184f49815e7efbcab5d8908b41",
    "model.safetensors": "53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db",
    "tokenizer.json": "be50c3628f2bf5bb5e3a7f17b1f74611b2561a3a27eeab05e5aa30f411572037",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def model_hashes(path: Path = MODEL_PATH) -> dict[str, str]:
    return {name: sha256_file(path / name) for name in EXPECTED_HASHES}


def assert_model_hashes(path: Path = MODEL_PATH) -> dict[str, str]:
    hashes = model_hashes(path)
    mismatch = {name: value for name, value in hashes.items() if value != EXPECTED_HASHES[name]}
    if mismatch:
        raise RuntimeError(f"G2.2 frozen encoder hash mismatch: {mismatch}")
    return hashes


@dataclass(frozen=True, slots=True)
class EncoderPreflight:
    model_path: str
    hashes: tuple[tuple[str, str], ...]
    hidden_size: int
    max_positions: int
    device: str
    deterministic: bool
    load_ms: float


class RawTokenEncoder(torch.nn.Module):
    """MiniLM token-state encoder, with explicit frozen and partial-tune modes."""

    def __init__(self, model_path: Path = MODEL_PATH, partial_tune: bool = False) -> None:
        super().__init__()
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        self.tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True, use_fast=True)
        self.model = AutoModel.from_pretrained(str(model_path), local_files_only=True)
        self.hidden_size = int(self.model.config.hidden_size)
        self.set_trainable(partial_tune)

    def set_trainable(self, partial_tune: bool) -> None:
        for parameter in self.model.parameters():
            parameter.requires_grad = False
        if not partial_tune:
            return
        # all-MiniLM-L6-v2 is BERT-shaped. Keep this explicit and fail closed for another layout.
        layers = getattr(getattr(self.model, "encoder", None), "layer", None)
        if layers is None or len(layers) < 2:
            raise RuntimeError("partial tuning requires BERT-like encoder.layer")
        for layer in layers[-2:]:
            for parameter in layer.parameters():
                parameter.requires_grad = True
        norm = getattr(self.model, "LayerNorm", None)
        if norm is not None:
            for parameter in norm.parameters():
                parameter.requires_grad = True

    def tokenize(self, texts: list[str]) -> dict[str, torch.Tensor]:
        encoded = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=128,
            return_offsets_mapping=True,
            return_tensors="pt",
        )
        return {key: value for key, value in encoded.items()}

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor, **kwargs: torch.Tensor) -> torch.Tensor:
        model_kwargs = {"input_ids": input_ids, "attention_mask": attention_mask}
        if "token_type_ids" in kwargs:
            model_kwargs["token_type_ids"] = kwargs["token_type_ids"]
        return self.model(**model_kwargs).last_hidden_state


def model_check(model_path: Path = MODEL_PATH) -> dict[str, object]:
    hashes = assert_model_hashes(model_path)
    torch.use_deterministic_algorithms(True, warn_only=True)
    start = time.perf_counter()
    encoder = RawTokenEncoder(model_path, partial_tune=False)
    load_ms = (time.perf_counter() - start) * 1000
    encoded = encoder.tokenize(["Qorim has a varel seal."])
    extra = {key: value for key, value in encoded.items() if key not in {"input_ids", "attention_mask", "offset_mapping"}}
    with torch.no_grad():
        first = encoder(encoded["input_ids"], encoded["attention_mask"], **extra)
        second = encoder(encoded["input_ids"], encoded["attention_mask"], **extra)
    if not torch.equal(first, second):
        raise RuntimeError("offline frozen encoder output was not deterministic")
    return {
        "model_path": str(model_path),
        "hashes": hashes,
        "hidden_size": encoder.hidden_size,
        "max_positions": int(encoder.model.config.max_position_embeddings),
        "device": "cpu",
        "deterministic": True,
        "load_ms": load_ms,
    }
