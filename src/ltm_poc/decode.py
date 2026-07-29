"""Evidence-bounded generation with deterministic extraction fallback."""

import re
from typing import Any

import torch

from ltm_poc.config import WorkspaceConfig
from ltm_poc.schemas import DecodedAnswer, EvidenceItem


def fallback(evidence: list[EvidenceItem], reason: str) -> DecodedAnswer:
    citations = [item.chunk_id for item in evidence]
    text = "\n".join(f"[{item.chunk_id}] {item.text}" for item in evidence)
    return DecodedAnswer(
        text=text or "No supporting evidence was found.",
        citation_chunk_ids=citations,
        decoder_model_id="extractive-fallback",
        used_fallback=True,
        fallback_reason=reason,
    )


def decode(
    prompt: str,
    evidence: list[EvidenceItem],
    tokenizer: Any,
    model: Any,
    device: str,
    config: WorkspaceConfig,
) -> DecodedAnswer:
    bounded = evidence[: config.evidence_limit]
    sources = "\n".join(
        f"[{item.chunk_id}] {item.text[: config.decoder_excerpt_tokens * 4]}"
        for item in bounded
    )
    instruction = (
        "Answer using only sources. Cite [chunk_id].\n"
        f"Question: {prompt}\nSources:\n{sources}"
    )
    try:
        tokens = tokenizer(
            instruction,
            return_tensors="pt",
            truncation=True,
            max_length=config.decoder_input_tokens,
        ).to(device)
        with torch.inference_mode():
            output = model.generate(
                **tokens,
                max_new_tokens=config.decoder_output_tokens,
                do_sample=False,
                num_beams=1,
                use_cache=True,
            )
        text = tokenizer.decode(output[0], skip_special_tokens=True).strip()
        cited = re.findall(r"\[([^\]]+)\]", text)
        allowed = {item.chunk_id for item in bounded}
        if not text or not cited or any(chunk_id not in allowed for chunk_id in cited):
            return fallback(bounded, "missing_or_invalid_citation")
        return DecodedAnswer(
            text=text,
            citation_chunk_ids=list(dict.fromkeys(cited)),
            decoder_model_id=config.decoder_model_id,
            used_fallback=False,
            fallback_reason=None,
        )
    except Exception as error:  # fallback is intentional at this trust boundary
        return fallback(bounded, f"decoder_error:{type(error).__name__}")
