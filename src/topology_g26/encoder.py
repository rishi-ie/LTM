"""Pinned local MiniLM boundary for G2.6."""

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


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def assert_model_hashes(path: Path = MODEL_PATH) -> dict[str, str]:
    found = {name: file_hash(path / name) for name in EXPECTED_HASHES}
    mismatches = {name: value for name, value in found.items() if value != EXPECTED_HASHES[name]}
    if mismatches:
        raise RuntimeError(f"G2.6 MiniLM hash mismatch: {mismatches}")
    return found


class OnePassMiniLM(torch.nn.Module):
    def __init__(self, model_path: Path = MODEL_PATH, *, trainable: bool = True) -> None:
        super().__init__()
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        self.tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True, use_fast=True)
        self.model = AutoModel.from_pretrained(str(model_path), local_files_only=True)
        self.hidden_size = int(self.model.config.hidden_size)
        self.forward_calls = 0
        for parameter in self.model.parameters():
            parameter.requires_grad = trainable

    def tokenize(self, texts: list[str]) -> dict[str, torch.Tensor]:
        return dict(self.tokenizer(texts, padding=True, truncation=True, max_length=128, return_offsets_mapping=True, return_tensors="pt"))

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor, **extra: torch.Tensor) -> torch.Tensor:
        self.forward_calls += 1
        token_type_ids = extra.get("token_type_ids")
        kwargs = {"token_type_ids": token_type_ids} if token_type_ids is not None else {}
        return self.model(input_ids=input_ids, attention_mask=attention_mask, **kwargs).last_hidden_state


def model_check(model_path: Path = MODEL_PATH) -> dict[str, object]:
    hashes = assert_model_hashes(model_path)
    torch.set_num_threads(4)
    torch.use_deterministic_algorithms(True, warn_only=True)
    start = time.perf_counter()
    encoder = OnePassMiniLM(model_path, trainable=False)
    load_ms = (time.perf_counter() - start) * 1000
    tokens = encoder.tokenize(["Qorim supports the varel claim."])
    offsets = tokens.pop("offset_mapping")
    with torch.no_grad():
        first = encoder(tokens["input_ids"], tokens["attention_mask"])
        second = encoder(tokens["input_ids"], tokens["attention_mask"])
    if not torch.equal(first, second):
        raise RuntimeError("local MiniLM is nondeterministic")
    return {"hashes": hashes, "hidden_size": encoder.hidden_size, "device": "cpu", "load_ms": load_ms, "token_count": int(tokens["attention_mask"].sum()), "offset_count": int(offsets.shape[1]), "deterministic": True}

