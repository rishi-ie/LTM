"""Gold-assisted oracle ladder used only by evaluator/development code."""

from __future__ import annotations

import torch

from .decode import decode_from_spans
from .metrics import link_metrics, sentence_metrics


def _gold_span_outputs(model, examples, confidence: float, margin: float):
    outputs = []
    model.eval()
    with torch.no_grad():
        for example in examples:
            encoded = model.encoder.tokenize([example.source.text])
            offsets = encoded.pop("offset_mapping")
            extra = {key: value for key, value in encoded.items() if key not in {"input_ids", "attention_mask"}}
            raw = model.encoder(encoded["input_ids"], encoded["attention_mask"], **extra)
            states = model.projection(raw)
            hub = (states * encoded["attention_mask"].unsqueeze(-1)).sum(1) / encoded["attention_mask"].sum(1, keepdim=True).clamp_min(1)
            outputs.append(
                decode_from_spans(
                    example.source,
                    example.gold.spans,
                    offsets,
                    raw,
                    states,
                    hub,
                    model.hierarchy,
                    confidence,
                    margin,
                )
            )
    return tuple(outputs)


def run_diagnostics(model, sentence_examples, link_examples, confidence: float = 0.0, margin: float = 0.0) -> dict[str, object]:
    """Return D1–D5 without exposing gold to the runtime compiler process."""
    d1 = _gold_span_outputs(model, sentence_examples, confidence, margin)
    d3 = model.forward(tuple(example.source for example in sentence_examples), confidence, margin)
    d4 = tuple(
        model.link(example.source, example.fragment_spans, example.public_candidates, confidence, margin)
        for example in link_examples
    )
    link_fragments = model.forward(tuple(example.source for example in link_examples), confidence, margin)
    predicted_fragments = []
    for example, result in zip(link_examples, link_fragments):
        fragments = result.hypotheses[0].spans if result.hypotheses else ()
        predicted_fragments.append(model.link(example.source, fragments, example.public_candidates, confidence, margin))
    # D2 uses gold boundaries and kinds predicted by the lattice.  The span F1
    # is the meaningful metric here; it isolates kind recovery from boundary
    # omission without injecting a topology relation.
    d2 = sentence_metrics(sentence_examples, d3)
    return {
        "D1_gold_spans_and_kinds": sentence_metrics(sentence_examples, d1),
        "D2_gold_boundaries_predicted_kinds": {
            "span_f1": d2["span_f1"],
            "span_offset_accuracy": d2["span_offset_accuracy"],
        },
        "D3_predicted_lattice": sentence_metrics(sentence_examples, d3),
        "D4_gold_sentence_ir_linker": link_metrics(link_examples, d4),
        "D5_predicted_sentence_ir_linker": link_metrics(link_examples, tuple(predicted_fragments)),
    }


def diagnostics_json(value: dict[str, object]) -> dict[str, object]:
    return value
