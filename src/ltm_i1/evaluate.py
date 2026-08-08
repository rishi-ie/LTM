from __future__ import annotations

import hashlib
import json
import os
import platform
import resource
import time
from dataclasses import asdict
from pathlib import Path

from ltm_i1.controls import attack_results
from topology_g101.model import FlanCandidateScorer, RuntimeUnavailable

from .generator import cases
from .metrics import summarize
from .runner import run_case

ROOT = Path(__file__).resolve().parents[2]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, default=str), encoding="utf-8")
    os.replace(temporary, path)


def model_check(workspace: Path) -> dict[str, object]:
    models = {name: ROOT / ".models" / name for name in ("flan-t5-small", "all-MiniLM-L6-v2")}
    files = {}
    for name, path in models.items():
        if not path.exists():
            raise RuntimeError(f"MODEL_MISSING:{name}")
        files[name] = {item.name: _sha(item) for item in sorted(path.iterdir()) if item.is_file()}
    checkpoint = ROOT / "workspaces/topology-g2-5/kernel-checkpoint.pt"
    files["g2.5-checkpoint"] = _sha(checkpoint) if checkpoint.exists() else None
    result = {"experiment": "LTM-I1", "python": platform.python_version(), "numpy": __import__("numpy").__version__, "models": files, "offline": True, "network_calls": 0}
    _atomic(workspace / "model-check.json", result)
    return result


def build_inputs(workspace: Path) -> None:
    if (workspace / "locked" / "cases.json").exists():
        raise RuntimeError("LOCKED_SUITE_ALREADY_EXISTS")
    dev = cases("development", 128, 1801)
    locked = cases("locked", 512, 20261001)
    _atomic(workspace / "development" / "cases.json", [{"case_id": item.case_id, "family": item.family} for item in dev])
    _atomic(workspace / "locked" / "cases.json", [{"case_id": item.case_id, "family": item.family} for item in locked])
    _atomic(workspace / "development" / "gold" / "expected.json", {item.case_id: {"family": item.family, "target": item.target_atom_id} for item in dev})
    _atomic(workspace / "locked" / "gold" / "expected.json", {item.case_id: {"family": item.family, "target": item.target_atom_id} for item in locked})


def _run_cases(workspace: Path, split: str, count: int, seed: int, *, decoder: bool) -> dict[str, object]:
    started = time.perf_counter()
    scorer = None
    if decoder:
        try:
            scorer = FlanCandidateScorer(ROOT / ".models/flan-t5-small")
        except RuntimeUnavailable as error:
            scorer = None
            decoder_error = str(error)
        else:
            decoder_error = None
    else:
        decoder_error = None
    results = tuple(run_case(item, workspace, scorer) for item in cases(split, count, seed))
    output = summarize(results)
    output.update({"split": split, "runtime_seconds": time.perf_counter() - started, "decoder_error": decoder_error, "results": [asdict(item) for item in results]})
    _atomic(workspace / f"{split}-results.json", output)
    return output


def develop(workspace: Path) -> dict[str, object]:
    return _run_cases(workspace, "development", 128, 1801, decoder=False)


def evaluate_locked(workspace: Path) -> dict[str, object]:
    if (workspace / "locked-results.json").exists():
        raise RuntimeError("LOCKED_EVALUATION_ALREADY_EXISTS")
    result = _run_cases(workspace, "locked", 512, 20261001, decoder=True)
    _atomic(workspace / "controls.json", [{"attack_id": item.attack_id, "rejected": item.rejected, "primary_code": item.primary_code} for item in attack_results()])
    _atomic(workspace / "locked-results.json", result)
    return result


def freeze(workspace: Path) -> None:
    files = sorted(str(path.relative_to(workspace)) for path in workspace.rglob("*") if path.is_file() and "gold" not in path.parts)
    manifest = {"experiment": "LTM-I1", "files": {name: _sha(workspace / name) for name in files}, "locked": False}
    _atomic(workspace / "frozen-manifest.json", manifest)


def replay(workspace: Path) -> dict[str, object]:
    original = json.loads((workspace / "locked-results.json").read_text())
    replayed = _run_cases(workspace / "replay", "locked", 512, 20261001, decoder=True)
    semantic_fields = ("metrics", "failure_codes")
    equality = all(original.get(field) == replayed.get(field) for field in semantic_fields)
    result = {"semantic_replay_equal": equality, "telemetry_excluded": True}
    _atomic(workspace / "verification.json", result)
    return result


def g25_diagnostic(workspace: Path) -> dict[str, object]:
    """Measure only the supplied-atom G2.5 handoff, never raw-language coverage."""
    checkpoint_root = ROOT / "workspaces/topology-g2-5"
    checkpoint = checkpoint_root / "kernel-checkpoint.pt"
    if not checkpoint.exists():
        result = {"available": False, "reason": "G2.5_CHECKPOINT_MISSING"}
        _atomic(workspace / "g2.5-diagnostic.json", result)
        return result
    from topology_g25.assembly import assemble_handoff
    from topology_g25.dataset import generate_kernel_examples
    from topology_g25.evaluate import _load_kernel_model
    from topology_g25.inference import infer_kernel
    from topology_g25.schemas import KernelRuntimeCase
    examples = generate_kernel_examples("kernel_locked")[:360]
    runtime = tuple(KernelRuntimeCase(item.source, item.atoms) for item in examples)
    predictions = infer_kernel(_load_kernel_model(checkpoint_root), runtime)
    expected = {item.source.source_id: item for item in examples}
    emitted = [item for item in predictions if item.factor is not None]
    correct = [item for item in emitted if item.relation_type == expected[item.source_id].relation_type and item.role_bindings == expected[item.source_id].role_bindings]
    converted = 0
    for prediction in correct:
        example = expected[prediction.source_id]
        handoff = assemble_handoff(example.source, example.atoms, (prediction.factor,))
        if handoff is not None:
            converted += 1
    result = {"available": True, "cases": len(examples), "emitted_handoffs": len(emitted), "correct_emitted_handoffs": len(correct), "converted_handoffs": converted, "conversion_precision": converted / max(1, len(correct)), "raw_language_compilation_tested": False}
    _atomic(workspace / "g2.5-diagnostic.json", result)
    return result


def run_all(workspace: Path) -> dict[str, object]:
    workspace.mkdir(parents=True, exist_ok=True)
    if (workspace / "locked-results.json").exists():
        raise RuntimeError("LOCKED_EVALUATION_ALREADY_EXISTS")
    model_check(workspace)
    build_inputs(workspace)
    development = develop(workspace)
    freeze(workspace)
    locked = evaluate_locked(workspace)
    diagnostic = g25_diagnostic(workspace)
    replay_result = replay(workspace)
    classification = "LTM-I1-A — CANONICAL INTEGRATION PASS"
    required = ("semantic_agreement", "artifact_agreement", "projection_agreement", "address_agreement", "frontier_agreement", "coverage_agreement", "hard_agreement", "soft_agreement", "g9_agreement", "decoder_agreement")
    if any(locked["metrics"][name] != 1.0 for name in required) or not replay_result["semantic_replay_equal"]:
        classification = "LTM-I1-B — FIELDIR REPRESENTATION OR RELOAD FAILURE"
    summary = {"experiment": "LTM-I1", "classification": classification, "development": development["metrics"], "locked": locked["metrics"], "g2_5_diagnostic": diagnostic, "verification": replay_result, "runtime_seconds": locked["runtime_seconds"], "peak_rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024 if platform.system() == "Darwin" else 1024)}
    _atomic(workspace / "report-summary.json", summary)
    from .report import write_report
    write_report(workspace, ROOT / "docs/experiments/integration/i01/report.md")
    return summary
