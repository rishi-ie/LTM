from __future__ import annotations

import hashlib
import os
import time
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


def assert_model_hashes(path: Path = MODEL_PATH) -> dict[str, str]:
    found = {name: sha256_file(path / name) for name in EXPECTED_HASHES}
    mismatch = {name: value for name, value in found.items() if value != EXPECTED_HASHES[name]}
    if mismatch:
        raise RuntimeError(f"G2.3 encoder hash mismatch: {mismatch}")
    return found


class FullTokenEncoder(torch.nn.Module):
    def __init__(self, model_path: Path = MODEL_PATH) -> None:
        super().__init__()
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        self.tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True, use_fast=True)
        self.model = AutoModel.from_pretrained(str(model_path), local_files_only=True)
        self.hidden_size = int(self.model.config.hidden_size)
        for parameter in self.model.parameters():
            parameter.requires_grad = True

    def tokenize(self, texts: list[str]) -> dict[str, torch.Tensor]:
        return dict(self.tokenizer(texts, padding=True, truncation=True, max_length=128, return_offsets_mapping=True, return_tensors="pt"))

    def tokenize_pairs(self, left: list[str], right: list[str]) -> dict[str, torch.Tensor]:
        if len(left) != len(right):
            raise ValueError("pair batches must have the same length")
        return dict(
            self.tokenizer(
                left,
                right,
                padding=True,
                truncation=True,
                max_length=128,
                return_tensors="pt",
            )
        )

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor, **kwargs: torch.Tensor) -> torch.Tensor:
        allowed = {key: value for key, value in kwargs.items() if key == "token_type_ids"}
        return self.model(input_ids=input_ids, attention_mask=attention_mask, **allowed).last_hidden_state


def model_check(model_path: Path = MODEL_PATH) -> dict[str, object]:
    hashes = assert_model_hashes(model_path)
    torch.use_deterministic_algorithms(True, warn_only=True)
    start = time.perf_counter(); encoder = FullTokenEncoder(model_path); load_ms = (time.perf_counter() - start) * 1000
    encoded = encoder.tokenize(["Qorim has the varel seal."]); offsets = encoded.pop("offset_mapping")
    extra = {key: value for key, value in encoded.items() if key not in {"input_ids", "attention_mask"}}
    with torch.no_grad():
        first = encoder(encoded["input_ids"], encoded["attention_mask"], **extra)
        second = encoder(encoded["input_ids"], encoded["attention_mask"], **extra)
    if not torch.equal(first, second):
        raise RuntimeError("MiniLM output is not deterministic")
    return {"model_path": str(model_path), "hashes": hashes, "hidden_size": encoder.hidden_size, "device": "cpu", "deterministic": True, "load_ms": load_ms, "tokens": int(encoded["attention_mask"].sum()), "offsets": int(offsets.shape[1])}
