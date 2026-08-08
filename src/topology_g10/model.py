from __future__ import annotations

import hashlib
import time
from pathlib import Path

EXPECTED = {
    "config.json": "b045e57ea90b8f1b35f89f954b176a5c1faa02bd0af2c89bcec191239d66cef4",
    "tokenizer.json": "a8506e7111b80c6d8635951a02eab0f4e1a8e4e5772da83846579e97b16f61bf",
    "model.safetensors": "ddffab9cbc7bf6dde941c6724841eeca8981fcfa81ca20ff8efff1396326d153",
}


class RuntimeUnavailable(RuntimeError): pass


def verify_files(path: Path) -> None:
    for name, expected in EXPECTED.items():
        file = path / name
        if not file.exists() or hashlib.sha256(file.read_bytes()).hexdigest() != expected: raise RuntimeUnavailable("MODEL_HASH_MISMATCH")


class Qwen:
    def __init__(self, path: Path):
        verify_files(path)
        try:
            from mlx_lm import generate, load
            self.model, self.tokenizer = load(str(path))
            self.generate = generate
        except Exception as error:
            raise RuntimeUnavailable(f"METAL_UNAVAILABLE:{type(error).__name__}") from error

    def complete(self, prompt: str, max_tokens: int) -> tuple[str, int, float]:
        started = time.perf_counter()
        try: text = self.generate(self.model, self.tokenizer, prompt, verbose=False, max_tokens=max_tokens)
        except Exception as error: raise RuntimeUnavailable(f"GENERATION_FAILED:{type(error).__name__}") from error
        return text.strip(), len(self.tokenizer.encode(text)), (time.perf_counter() - started) * 1000
