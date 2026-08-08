"""Offline, frozen MiniLM boundary for G2.7."""

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
    if found != EXPECTED_HASHES:
        raise RuntimeError(f"G2.7 frozen MiniLM hash mismatch: {found}")
    return found


class FrozenMiniLM(torch.nn.Module):
    def __init__(self, path: Path = MODEL_PATH) -> None:
        super().__init__()
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        self.tokenizer = AutoTokenizer.from_pretrained(str(path), local_files_only=True, use_fast=True)
        self.model = AutoModel.from_pretrained(str(path), local_files_only=True)
        self.hidden_size = int(self.model.config.hidden_size)
        self.forward_calls = 0
        for parameter in self.model.parameters():
            parameter.requires_grad = False
        self.model.eval()

    def tokenize(self, texts: list[str]) -> dict[str, torch.Tensor]:
        return dict(self.tokenizer(texts, padding=True, truncation=True, max_length=128, return_offsets_mapping=True, return_tensors="pt"))

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor, **extra: torch.Tensor) -> torch.Tensor:
        self.forward_calls += 1
        kwargs = {"token_type_ids": extra["token_type_ids"]} if "token_type_ids" in extra else {}
        with torch.no_grad():
            return self.model(input_ids=input_ids, attention_mask=attention_mask, **kwargs).last_hidden_state


def model_check() -> dict[str, object]:
    hashes = assert_model_hashes()
    torch.set_num_threads(4)
    torch.use_deterministic_algorithms(True, warn_only=True)
    start = time.perf_counter()
    encoder = FrozenMiniLM()
    tokens = encoder.tokenize(["Qorim supports the varel claim."])
    tokens.pop("offset_mapping")
    first = encoder(tokens["input_ids"], tokens["attention_mask"])
    second = encoder(tokens["input_ids"], tokens["attention_mask"])
    if not torch.equal(first, second) or any(parameter.requires_grad for parameter in encoder.model.parameters()):
        raise RuntimeError("frozen MiniLM preflight failed")
    return {"hashes": hashes, "hidden_size": encoder.hidden_size, "device": "cpu", "load_ms": (time.perf_counter() - start) * 1000, "deterministic": True, "forward_calls": encoder.forward_calls}
