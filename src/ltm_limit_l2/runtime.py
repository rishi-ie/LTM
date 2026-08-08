"""Proof handoff that preserves the frozen I3.1 search contract."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import torch

from ltm_inference_i31.dataset import feature
from ltm_inference_i31.field import MathFieldIndex, build_field
from ltm_inference_i31.formal import body_hash, verify_proof
from ltm_inference_i31.kernel import SearchKernel
from ltm_inference_i31.runtime import infer
from ltm_inference_i31.schemas import MathematicalBody

from .schemas import CompiledMathBody, CompiledMathQuestion, L2InferenceResult


def _runtime_body(body: CompiledMathBody, index: int) -> MathematicalBody:
    item = MathematicalBody(body.body_id, body.reality_key, body.left, body.right, body_hash(MathematicalBody(body.body_id, body.reality_key, body.left, body.right, body.provenance_hash, index)), index)
    return item


def _model(checkpoint: Path | None) -> SearchKernel:
    model = SearchKernel()
    if checkpoint is not None and checkpoint.exists():
        model.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True))
    return model.eval()


def prove(question: CompiledMathQuestion, bodies: tuple[CompiledMathBody, ...], checkpoint: Path | None = None) -> L2InferenceResult:
    if question.theorem_problem is None:
        return L2InferenceResult(question, None, False, None, None, "clarification_required", question.failure_codes)
    runtime_bodies = tuple(_runtime_body(body, index) for index, body in enumerate(bodies))
    vectors = np.asarray([np.concatenate((feature(body.left), feature(body.right))) for body in runtime_bodies], dtype=np.float32)
    field = MathFieldIndex(runtime_bodies, vectors, build_field(runtime_bodies, vectors))
    result = infer(question.theorem_problem, field, _model(checkpoint), use_goal=True, use_heuristic=True, use_scorer=True, prefer_reductions=False)
    replay = bool(result.disposition == "proved" and verify_proof(question.theorem_problem.source, question.theorem_problem.goal, result.proof, {item.body_id: item for item in runtime_bodies}, question.theorem_problem.reality_key))
    proof_hash = hashlib.sha256(repr(result.proof).encode()).hexdigest() if replay else None
    return L2InferenceResult(question, result, replay, proof_hash, "verified" if replay else None, "proved" if replay else result.disposition, () if replay else result.failure_codes)
