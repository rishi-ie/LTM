"""Frozen confidence calibration for fail-closed atomic sentence commits."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .metrics import sentence_metrics
from .schemas import SentenceCompilationResult, SentenceExample


@dataclass(frozen=True, slots=True)
class Calibration:
    graph_confidence: float
    graph_margin: float
    link_confidence: float
    link_margin: float
    accepted_precision: float
    safe_coverage: float


def _apply_sentence_thresholds(
    examples: tuple[SentenceExample, ...],
    raw: tuple[SentenceCompilationResult, ...],
    confidence: float,
    margin: float,
) -> tuple[SentenceCompilationResult, ...]:
    adjusted = []
    for example, result in zip(examples, raw):
        if result.disposition != "accept" or not result.hypotheses:
            adjusted.append(result)
            continue
        hypothesis = result.hypotheses[0]
        if hypothesis.probability >= confidence and hypothesis.margin >= margin:
            adjusted.append(result)
        else:
            adjusted.append(
                SentenceCompilationResult(
                    result.source_id,
                    result.hypotheses,
                    None,
                    "clarification_required",
                    ("CALIBRATION_ABSTENTION",),
                    result.runtime_ms,
                    result.token_count,
                )
            )
    return tuple(adjusted)


def calibrate(
    examples: tuple[SentenceExample, ...],
    raw: tuple[SentenceCompilationResult, ...],
) -> Calibration:
    """Select the most coverage-preserving threshold with zero unsafe commits."""
    choices: list[Calibration] = []
    for confidence_step in range(70, 100):
        confidence = confidence_step / 100
        for margin_step in range(5, 31, 5):
            margin = margin_step / 100
            metrics = sentence_metrics(examples, _apply_sentence_thresholds(examples, raw, confidence, margin))
            if (
                metrics["accepted_exact_precision"] >= 0.99
                and metrics["high_severity_polarity_errors"] == 0
                and metrics["silent_invalid_insertions"] == 0
            ):
                choices.append(Calibration(confidence, margin, confidence, margin, metrics["accepted_exact_precision"], metrics["safe_coverage"]))
    if not choices:
        # This is intentionally a fail-closed calibration, not a quality
        # workaround: no threshold can authorize an unsafe model.
        return Calibration(1.0, 1.0, 1.0, 1.0, 0.0, 0.0)
    return max(choices, key=lambda item: (item.safe_coverage, -item.graph_confidence, -item.graph_margin))


def calibration_json(value: Calibration) -> dict[str, float]:
    return asdict(value)
