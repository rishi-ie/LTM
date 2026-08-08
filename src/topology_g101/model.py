"""Frozen FLAN-T5 candidate scorer; it never generates text."""

from __future__ import annotations

import time
from pathlib import Path


class RuntimeUnavailable(RuntimeError):
    pass


class FlanCandidateScorer:
    def __init__(self, model_path: Path) -> None:
        try:
            import torch
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
            self.torch = torch
            self.tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(model_path, local_files_only=True)
            self.model.eval()
            for parameter in self.model.parameters():
                parameter.requires_grad_(False)
        except Exception as error:
            raise RuntimeUnavailable(f"COMPACT_MODEL_UNAVAILABLE:{type(error).__name__}") from error

    def score(self, mr_text: str, candidate_text: str) -> tuple[float, int, float]:
        started = time.perf_counter()
        inputs = self.tokenizer(mr_text, return_tensors="pt")
        labels = self.tokenizer(candidate_text, return_tensors="pt").input_ids
        with self.torch.no_grad():
            output = self.model(**inputs, labels=labels)
        token_count = int(labels.numel())
        return -float(output.loss) * token_count / max(1, token_count), token_count, (time.perf_counter() - started) * 1000
