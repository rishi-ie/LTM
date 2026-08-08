from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ltm_inference_i23.dataset import build_split, load_jsonl, semantic_vector
from ltm_inference_i23.field import PublicField
from ltm_inference_i23.kernel import save_kernel, train_kernel
from ltm_inference_i23.lifecycle import _load_public
from ltm_inference_i23.runtime import infer
from ltm_inference_i23.schemas import AtomicMumbrane, ReasoningBody, RuntimePrompt


def test_opaque_vectors_have_no_ordinal_state_argument() -> None:
    first = semantic_vector("opaque-alpha", "global")
    second = semantic_vector("opaque-alpha", "global")
    other = semantic_vector("opaque-beta", "global")
    assert first.shape == (384,)
    assert (first == second).all()
    assert not (first == other).all()


def test_public_archive_excludes_gold_and_runtime_source(tmp_path: Path) -> None:
    build_split(tmp_path, "development", 128, 32, 31)
    public = tmp_path / "public" / "development"
    gold = tmp_path / "evaluator-gold" / "development" / "gold.jsonl"
    public_rows = load_jsonl(public / "prompts.jsonl")
    assert gold.exists()
    assert all("gold_candidate_id" not in row and "required_body_ids" not in row for row in public_rows)
    runtime_source = Path(__file__).resolve().parents[2] / "src/ltm_inference_i23/runtime.py"
    assert "evaluator-gold" not in runtime_source.read_text(encoding="utf-8")


def test_learned_summary_field_is_bounded_and_moves_state(tmp_path: Path) -> None:
    build_split(tmp_path, "development", 128, 32, 37)
    field, rows = _load_public(tmp_path, "development")
    model, _ = train_kernel(field, steps=4, batch_size=32, seed=37, learning_rate=.0003)
    field.refresh(model)
    assert field.membership_ok()
    prompt = RuntimePrompt(str(rows[1]["prompt_id"]), tuple(rows[1]["clamped_unit_ids"]), str(rows[1]["scope_key"]), 64, 32)
    result = infer(field, model, prompt, source_threshold=.95)
    assert not result.factual_operations
    assert all(len(step.opened_cell_ids) >= 1 for step in result.trajectory)


def test_field_does_not_need_identity_lookup() -> None:
    left = AtomicMumbrane("a", "body", 0, 0, 0, "positive", "observed", "global", "opaque:a", "p")
    right = AtomicMumbrane("b", "body", 1, 1, 1, "positive", "observed", "global", "opaque:b", "p")
    body = ReasoningBody("body", ("a", "b"), "global", "source", "hash")
    field = PublicField((body,), (left, right), semantic_vector("opaque:a", "global").reshape(1, -1).repeat(2, axis=0))
    assert not hasattr(field, "by_source_identity")


def test_runtime_and_evaluator_are_separate_commands(tmp_path: Path) -> None:
    build_split(tmp_path, "locked", 128, 32, 41)
    field, _ = _load_public(tmp_path, "locked")
    model, losses = train_kernel(field, steps=2, batch_size=16, seed=41, learning_rate=.0003)
    save_kernel(tmp_path / "selected-kernel.pt", model, losses, 41)
    root = Path(__file__).resolve().parents[2]
    for command in ("runtime-infer", "evaluator-score"):
        subprocess.run([sys.executable, "-m", "ltm_inference_i23", command, "--workspace", str(tmp_path), "--offline"], cwd=root, check=True)
    prediction = json.loads((tmp_path / "runtime-output" / "locked-predictions.json").read_text(encoding="utf-8"))
    locked = json.loads((tmp_path / "locked-results.json").read_text(encoding="utf-8"))
    assert prediction["public_prompts"] == 32
    assert locked["metrics"]["cases"] == 32
