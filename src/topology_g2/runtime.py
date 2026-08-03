from __future__ import annotations

import time
from pathlib import Path

from .prompts import prompt
from .schemas import ContextSnapshot, SourceRecord

MODEL_DIR = Path(__file__).resolve().parents[2] / ".models/Qwen2.5-0.5B-Instruct-mlx-4bit"


class ModelRuntime:
    def __init__(self, model_dir: Path = MODEL_DIR) -> None:
        from mlx_lm import load

        self.model, self.tokenizer = load(str(model_dir))

    def generate(self, text: str) -> tuple[str, float, int]:
        from mlx_lm import generate
        from mlx_lm.sample_utils import make_sampler

        started = time.perf_counter()
        # Qwen is an instruction-tuned chat model.  Supplying the compiler
        # contract as a bare completion prompt makes it continue arbitrary
        # JSON fragments rather than answer the extraction task.
        rendered = self.tokenizer.apply_chat_template(
            [{"role": "system", "content": text}],
            tokenize=False,
            add_generation_prompt=True,
        )
        output = generate(self.model, self.tokenizer, prompt=rendered, max_tokens=320, sampler=make_sampler(temp=0.0), verbose=False)
        elapsed = (time.perf_counter() - started) * 1000
        tokens = len(self.tokenizer.encode(output))
        return output, elapsed, tokens

    def compile(self, variant: int, source: SourceRecord, context: ContextSnapshot, invalid: str | None = None, errors: tuple[str, ...] = ()) -> tuple[str, float, int]:
        return self.generate(prompt(variant, source, context, invalid, errors))
