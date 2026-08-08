"""Canonical JSON codecs shared by public and evaluator processes."""

from __future__ import annotations

import json
from pathlib import Path

from ltm_inference_i3.dataset import expr_from_obj, expr_to_obj

from .schemas import ExactAxiomApplication, L4InferenceResult, L4Problem, L4ProofStep, L4SearchTrace


def problem_to_obj(value: L4Problem) -> dict[str, object]:
    return {
        "problem_id": value.problem_id,
        "source": expr_to_obj(value.source),
        "goal": expr_to_obj(value.goal),
        "reality_key": value.reality_key,
        "maximum_steps": value.maximum_steps,
        "maximum_bodies_per_state": value.maximum_bodies_per_state,
        "maximum_legal_proposals": value.maximum_legal_proposals,
        "beam_width": value.beam_width,
    }


def problem_from_obj(value: dict[str, object]) -> L4Problem:
    return L4Problem(
        str(value["problem_id"]),
        expr_from_obj(value["source"]),
        expr_from_obj(value["goal"]),
        str(value["reality_key"]),
        int(value["maximum_steps"]),
        int(value["maximum_bodies_per_state"]),
        int(value["maximum_legal_proposals"]),
        int(value["beam_width"]),
    )


def step_to_obj(value: L4ProofStep) -> dict[str, object]:
    application = value.application
    return {
        "application": {
            "body_id": application.body_id,
            "axiom_id": application.axiom_id,
            "site_path": list(application.site_path),
            "reverse": application.reverse,
            "substitution_hash": application.substitution_hash,
            "before_hash": application.before_hash,
            "after_hash": application.after_hash,
        },
        "before": expr_to_obj(value.before),
        "after": expr_to_obj(value.after),
    }


def step_from_obj(value: dict[str, object]) -> L4ProofStep:
    item = value["application"]
    application = ExactAxiomApplication(
        str(item["body_id"]),
        str(item["axiom_id"]),
        tuple(int(part) for part in item["site_path"]),
        bool(item["reverse"]),
        str(item["substitution_hash"]),
        str(item["before_hash"]),
        str(item["after_hash"]),
    )
    return L4ProofStep(application, expr_from_obj(value["before"]), expr_from_obj(value["after"]))


def application_to_obj(value: ExactAxiomApplication) -> dict[str, object]:
    return {
        "body_id": value.body_id,
        "axiom_id": value.axiom_id,
        "site_path": list(value.site_path),
        "reverse": value.reverse,
        "substitution_hash": value.substitution_hash,
        "before_hash": value.before_hash,
        "after_hash": value.after_hash,
    }


def application_from_obj(value: dict[str, object]) -> ExactAxiomApplication:
    return ExactAxiomApplication(
        str(value["body_id"]),
        str(value["axiom_id"]),
        tuple(int(item) for item in value["site_path"]),
        bool(value["reverse"]),
        str(value["substitution_hash"]),
        str(value["before_hash"]),
        str(value["after_hash"]),
    )


def result_to_obj(value: L4InferenceResult) -> dict[str, object]:
    return {
        "problem_id": value.problem_id,
        "disposition": value.disposition,
        "proof": [step_to_obj(item) for item in value.proof],
        "states_explored": value.states_explored,
        "bodies_opened": list(value.bodies_opened),
        "traces": [
            {
                "step": item.step,
                "state_hash": item.state_hash,
                "legal_proposal_count": item.legal_proposal_count,
                "retained_proposals": [application_to_obj(row) for row in item.retained_proposals],
                "beam_state_hashes": list(item.beam_state_hashes),
                "bodies_opened": list(item.bodies_opened),
            }
            for item in value.traces
        ],
        "failure_codes": list(value.failure_codes),
        "factual_operations": [],
    }


def result_from_obj(value: dict[str, object]) -> L4InferenceResult:
    traces = tuple(
        L4SearchTrace(
            int(item["step"]),
            str(item["state_hash"]),
            int(item["legal_proposal_count"]),
            tuple(application_from_obj(row) for row in item["retained_proposals"]),
            tuple(str(row) for row in item["beam_state_hashes"]),
            tuple(str(row) for row in item["bodies_opened"]),
        )
        for item in value["traces"]
    )
    return L4InferenceResult(
        str(value["problem_id"]),
        str(value["disposition"]),
        tuple(step_from_obj(item) for item in value["proof"]),
        int(value["states_explored"]),
        tuple(str(item) for item in value["bodies_opened"]),
        traces,
        tuple(str(item) for item in value["failure_codes"]),
    )


def write_jsonl(path: Path, rows: tuple[dict[str, object], ...], *, overwrite: bool = True) -> None:
    if path.exists() and not overwrite:
        raise RuntimeError(f"IMMUTABLE_ARTIFACT:{path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def read_jsonl(path: Path) -> tuple[dict[str, object], ...]:
    return tuple(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line)
