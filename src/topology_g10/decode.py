from __future__ import annotations

from .model import Qwen
from .prompting import render
from .schemas import DecoderBundle, DecoderResult, GenerationRecord
from .validator import fallback, validate


def decode(bundle: DecoderBundle, model: Qwen, settings: dict, *, method: str = "full") -> DecoderResult:
    original, tokens, elapsed = model.complete(render(bundle, method), settings["max_tokens"])
    validation = validate(original, bundle)
    repair_text = None
    final = original; used_fallback = False
    if method == "full" and not validation.accepted:
        repair_text, repair_tokens, repair_elapsed = model.complete(render(bundle, method, validation.errors), settings["max_tokens"])
        tokens += repair_tokens; elapsed += repair_elapsed; repaired = validate(repair_text, bundle)
        if repaired.accepted: final, validation = repair_text, repaired
        else: final, validation, used_fallback = fallback(bundle), validate(fallback(bundle), bundle), True
    disposition = bundle.required_disposition if validation.accepted else "rejected"
    return DecoderResult(bundle.bundle_id, final, validation, GenerationRecord(method, original, repair_text, tokens, elapsed), used_fallback, disposition)
