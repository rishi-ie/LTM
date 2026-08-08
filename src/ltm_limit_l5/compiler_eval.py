"""Independent controlled-language panel for the actual L5 compiler boundary."""

from __future__ import annotations

import hashlib
import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from .compiler import (
    CompiledSourceCoordinate,
    ControlledCompilerSource,
    CoordinateEncoder,
    SharedCoordinateCompiler,
    controlled_source,
)
from .schemas import CompiledPromptField


def atom_semantic_key(value: str) -> str:
    return "atom:" + hashlib.sha256(value.encode()).hexdigest()


_WORDS = (
    "amber", "birch", "cobalt", "delta", "ember", "falcon", "garden", "harbor",
    "island", "jasmine", "kernel", "lantern", "meadow", "nectar", "olive", "pebble",
    "quartz", "river", "saffron", "timber", "umber", "violet", "willow", "xenon",
    "yellow", "zephyr", "anchor", "breeze", "canyon", "dawn", "elm", "forest",
)


def controlled_atom(seed: int, group: int, role: str) -> str:
    """Return a lexical but split-disjoint atom that MiniLM can actually see."""

    raw = hashlib.sha256(f"{seed}|{group}|{role}".encode()).digest()
    parts = ".".join(_WORDS[value % len(_WORDS)] for value in raw[:5])
    return f"{role}.{parts}"


@dataclass(frozen=True, slots=True)
class RawCompilerCase:
    case_id: str
    source: ControlledCompilerSource
    mode: str
    should_accept: bool
    expected_input_keys: tuple[str, ...]
    expected_outcome_keys: tuple[str, ...]
    alignment_group: str | None


def build_compiler_panel(count: int, seed: int, *, split: str) -> tuple[RawCompilerCase, ...]:
    """Create split-disjoint valid pairs and fail-closed invalid inputs."""

    if count < 10:
        raise ValueError("compiler panel requires at least ten items")
    valid_count = count - max(2, count // 5)
    valid_count -= valid_count % 2
    rows: list[RawCompilerCase] = []
    for group in range(valid_count // 2):
        left = controlled_atom(seed, group, "condition")
        right = controlled_atom(seed, group, "outcome")
        reality = f"reality:{split}:{group % 7}"
        alignment = f"pair:{group}"
        body = controlled_source(
            f"when {left} then {right}",
            source_id=f"{split}:source:{group}",
            reality_key=reality,
            provenance_id=f"{split}:document:{group}",
        )
        prompt = controlled_source(
            f"given {left}, what follows?",
            source_id=f"{split}:prompt:{group}",
            reality_key=reality,
            provenance_id=f"{split}:request:{group}",
        )
        rows.extend(
            (
                RawCompilerCase(
                    body.source_id,
                    body,
                    "source",
                    True,
                    (atom_semantic_key(left),),
                    (atom_semantic_key(right),),
                    alignment,
                ),
                RawCompilerCase(
                    prompt.source_id,
                    prompt,
                    "prompt",
                    True,
                    (atom_semantic_key(left),),
                    (),
                    alignment,
                ),
            )
        )
    invalid_forms = (
        "what is the answer?",
        "when condition and then outcome",
        "given , what follows?",
        "given condition, what follows? answer=outcome",
        "when route_identifier then outcome",
    )
    for index in range(count - len(rows)):
        text = invalid_forms[index % len(invalid_forms)]
        source = controlled_source(
            text,
            source_id=f"{split}:invalid:{index}",
            reality_key=f"reality:{split}:invalid",
        )
        rows.append(
            RawCompilerCase(source.source_id, source, "prompt", False, (), (), None)
        )
    return tuple(rows)


def _compile(
    compiler: SharedCoordinateCompiler,
    case: RawCompilerCase,
) -> CompiledSourceCoordinate | CompiledPromptField:
    return (
        compiler.compile_source(case.source)
        if case.mode == "source"
        else compiler.compile_prompt(case.source)
    )


def evaluate_compiler_panel(
    cases: tuple[RawCompilerCase, ...],
    encoder: CoordinateEncoder,
) -> dict[str, object]:
    """Measure exact compilation and shared-coordinate retrieval separately."""

    compiler = SharedCoordinateCompiler(encoder)
    outputs = tuple(_compile(compiler, case) for case in cases)
    accepted = [
        (case, output)
        for case, output in zip(cases, outputs, strict=True)
        if output.disposition == "accept"
    ]
    incorrect_accepts = 0
    exact_valid = 0
    safe = 0
    source_positions: dict[str, tuple[float, ...]] = {}
    prompt_positions: dict[str, tuple[float, ...]] = {}
    for case, output in zip(cases, outputs, strict=True):
        accepted_now = output.disposition == "accept"
        exact = False
        if case.should_accept and accepted_now:
            if isinstance(output, CompiledSourceCoordinate):
                content = output.content
                exact = bool(
                    content is not None
                    and content.input_keys == case.expected_input_keys
                    and content.outcome_keys == case.expected_outcome_keys
                    and output.scope_key == case.source.scope_key
                    and output.reality_key == case.source.reality_key
                    and output.provenance_id == case.source.provenance_id
                )
                if exact and case.alignment_group is not None:
                    source_positions[case.alignment_group] = output.semantic_position
            else:
                exact = (
                    tuple(item.semantic_key for item in output.influences)
                    == case.expected_input_keys
                    and all(item.scope_key == case.source.scope_key for item in output.influences)
                    and all(item.reality_key == case.source.reality_key for item in output.influences)
                    and all(item.provenance_id == case.source.provenance_id for item in output.influences)
                )
                if exact and case.alignment_group is not None:
                    prompt_positions[case.alignment_group] = output.anchor_position
            exact_valid += int(exact)
        elif not case.should_accept and not accepted_now:
            exact = True
        if accepted_now and (not case.should_accept or not exact):
            incorrect_accepts += 1
        safe += int(exact)
    accepted_correct = len(accepted) - incorrect_accepts
    valid_cases = sum(item.should_accept for item in cases)
    recalls = []
    source_rows = tuple(sorted(source_positions.items()))
    for group, prompt in sorted(prompt_positions.items()):
        scored = sorted(
            (
                (
                    float(
                        np.dot(prompt, position)
                        / max(1e-12, math.sqrt(np.dot(prompt, prompt) * np.dot(position, position)))
                    ),
                    candidate_group,
                )
                for candidate_group, position in source_rows
            ),
            reverse=True,
        )
        recalls.append(group in {candidate for _score, candidate in scored[:8]})
    return {
        "cases": len(cases),
        "valid_cases": valid_cases,
        "accepted_cases": len(accepted),
        "accepted_semantic_precision": accepted_correct / len(accepted) if accepted else 1.0,
        "safe_coverage": safe / len(cases) if cases else 1.0,
        "exact_content_agreement": exact_valid / valid_cases if valid_cases else 1.0,
        "coordinate_recall_at_8": sum(recalls) / len(recalls) if recalls else 0.0,
        "incorrect_accepted_compilations": incorrect_accepts,
        "encoder_calls": encoder.forward_calls,
        "expected_encoder_calls": len(cases),
    }


def compiler_public_payload(case: RawCompilerCase) -> dict[str, object]:
    return {"case_id": case.case_id, "source": asdict(case.source), "mode": case.mode}


def compiler_gold_payload(case: RawCompilerCase) -> dict[str, object]:
    return {
        "case_id": case.case_id,
        "should_accept": case.should_accept,
        "expected_input_keys": case.expected_input_keys,
        "expected_outcome_keys": case.expected_outcome_keys,
        "alignment_group": case.alignment_group,
    }


def compile_public_payloads(
    rows: tuple[dict[str, object], ...],
    encoder: CoordinateEncoder,
) -> tuple[dict[str, object], ...]:
    """Runtime compiler path: accepts raw public rows and no expected fields."""

    compiler = SharedCoordinateCompiler(encoder)
    predictions = []
    for row in rows:
        source_row = row["source"]
        if not isinstance(source_row, dict):
            raise TypeError("invalid public compiler source")
        source = ControlledCompilerSource(**source_row)
        mode = str(row["mode"])
        output = (
            compiler.compile_source(source)
            if mode == "source"
            else compiler.compile_prompt(source)
        )
        if isinstance(output, CompiledSourceCoordinate):
            content = output.content
            input_keys = content.input_keys if content is not None else ()
            outcome_keys = content.outcome_keys if content is not None else ()
            position = output.semantic_position
            scope_key = output.scope_key
            reality_key = output.reality_key
            provenance_id = output.provenance_id
        else:
            input_keys = tuple(item.semantic_key for item in output.influences)
            outcome_keys = ()
            position = output.anchor_position
            scope_key = output.influences[0].scope_key if output.influences else source.scope_key
            reality_key = output.influences[0].reality_key if output.influences else source.reality_key
            provenance_id = output.influences[0].provenance_id if output.influences else source.provenance_id
        predictions.append(
            {
                "case_id": row["case_id"],
                "mode": mode,
                "disposition": output.disposition,
                "input_keys": input_keys,
                "outcome_keys": outcome_keys,
                "position": position,
                "scope_key": scope_key,
                "reality_key": reality_key,
                "provenance_id": provenance_id,
                "encoder_calls": output.encoder_calls,
            }
        )
    return tuple(predictions)


def score_compiler_predictions(
    public_rows: tuple[dict[str, object], ...],
    gold_rows: tuple[dict[str, object], ...],
    predictions: tuple[dict[str, object], ...],
) -> dict[str, object]:
    if not (len(public_rows) == len(gold_rows) == len(predictions)):
        raise ValueError("compiler public/gold/prediction length mismatch")
    accepted = incorrect = exact_valid = safe = valid = 0
    sources: dict[str, np.ndarray] = {}
    prompts: dict[str, np.ndarray] = {}
    for public, gold, predicted in zip(public_rows, gold_rows, predictions, strict=True):
        if public["case_id"] != gold["case_id"] or public["case_id"] != predicted["case_id"]:
            raise ValueError("compiler case identity mismatch")
        source = public["source"]
        if not isinstance(source, dict):
            raise TypeError("invalid compiler public source")
        should_accept = bool(gold["should_accept"])
        accepted_now = predicted["disposition"] == "accept"
        accepted += int(accepted_now)
        valid += int(should_accept)
        exact = (
            accepted_now
            and tuple(predicted["input_keys"]) == tuple(gold["expected_input_keys"])
            and tuple(predicted["outcome_keys"]) == tuple(gold["expected_outcome_keys"])
            and predicted["scope_key"] == source["scope_key"]
            and predicted["reality_key"] == source["reality_key"]
            and predicted["provenance_id"] == source["provenance_id"]
            and predicted["encoder_calls"] == 1
        )
        if should_accept:
            exact_valid += int(exact)
            safe += int(exact)
        else:
            safe += int(not accepted_now)
        incorrect += int(accepted_now and (not should_accept or not exact))
        group = gold["alignment_group"]
        if exact and group is not None:
            target = sources if public["mode"] == "source" else prompts
            target[str(group)] = np.asarray(predicted["position"], dtype=np.float32)
    recall = 0
    for group, prompt in prompts.items():
        ranked = sorted(
            ((float(np.dot(prompt, row)), key) for key, row in sources.items()),
            reverse=True,
        )[:8]
        recall += int(group in {key for _score, key in ranked})
    accepted_correct = accepted - incorrect
    return {
        "cases": len(public_rows),
        "valid_cases": valid,
        "accepted_cases": accepted,
        "accepted_semantic_precision": accepted_correct / accepted if accepted else 1.0,
        "safe_coverage": safe / len(public_rows) if public_rows else 1.0,
        "exact_content_agreement": exact_valid / valid if valid else 1.0,
        "coordinate_recall_at_8": recall / len(prompts) if prompts else 0.0,
        "incorrect_accepted_compilations": incorrect,
        "encoder_calls": sum(int(item["encoder_calls"]) for item in predictions),
        "expected_encoder_calls": len(predictions),
    }


def encode_compiler_panel(
    cases: tuple[RawCompilerCase, ...],
    model_path: Path,
    *,
    batch_size: int = 64,
) -> dict[str, np.ndarray]:
    """Batch the frozen local encoder while preserving one logical row per item."""

    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(str(model_path), local_files_only=True, device="cpu")
    rows = model.encode(
        [item.source.text for item in cases],
        batch_size=batch_size,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    ).astype(np.float32)
    if rows.shape != (len(cases), 384) or not np.isfinite(rows).all():
        raise ValueError("invalid compiler semantic rows")
    return {item.source.source_id: row for item, row in zip(cases, rows, strict=True)}


def encode_compiler_public_payloads(
    rows: tuple[dict[str, object], ...],
    model_path: Path,
    *,
    batch_size: int = 64,
) -> dict[str, np.ndarray]:
    sources = []
    for row in rows:
        value = row["source"]
        if not isinstance(value, dict):
            raise TypeError("invalid public compiler source")
        sources.append(ControlledCompilerSource(**value))
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(str(model_path), local_files_only=True, device="cpu")
    encoded = model.encode(
        [item.text for item in sources],
        batch_size=batch_size,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    ).astype(np.float32)
    if encoded.shape != (len(sources), 384) or not np.isfinite(encoded).all():
        raise ValueError("invalid compiler semantic rows")
    return {item.source_id: value for item, value in zip(sources, encoded, strict=True)}


__all__ = [
    "RawCompilerCase",
    "atom_semantic_key",
    "build_compiler_panel",
    "compile_public_payloads",
    "compiler_gold_payload",
    "compiler_public_payload",
    "controlled_atom",
    "encode_compiler_panel",
    "encode_compiler_public_payloads",
    "evaluate_compiler_panel",
    "score_compiler_predictions",
]
