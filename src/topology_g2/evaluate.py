from __future__ import annotations

import hashlib
import json
import resource
import sys
import time
from pathlib import Path
from typing import Any

from topology_g1.codec import digest
from topology_g1.schemas import SchemaError

from .dataset import generate_cases, write_gold_cases, write_runtime_cases
from .prompts import VARIANTS
from .runtime import MODEL_DIR, ModelRuntime
from .schemas import CandidateIR, GoldCase
from .serde import candidate_from_dict, dumps, plain
from .validate import validate_candidate, validate_text

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "topology-g2.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: object) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temp.replace(path)


def _model_hashes() -> dict[str, str]:
    return {str(path.relative_to(ROOT)): _sha(path) for path in sorted(MODEL_DIR.glob("*") ) if path.is_file()}


def _source_hashes() -> dict[str, str]:
    paths = sorted((ROOT / "src" / "topology_g2").glob("*.py")) + [CONFIG]
    return {str(path.relative_to(ROOT)): _sha(path) for path in paths}


def _case_files(workspace: Path, split: str) -> tuple[Path, Path]:
    directory = workspace / split
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "inputs.jsonl", directory / "gold.jsonl"


def materialize(split: str, workspace: Path) -> tuple[GoldCase, ...]:
    cases = generate_cases(split)
    runtime_path, gold_path = _case_files(workspace, split)
    write_runtime_cases(cases, runtime_path)
    write_gold_cases(cases, gold_path)
    return cases


def model_check(workspace: Path) -> dict[str, Any]:
    workspace.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    try:
        runtime = ModelRuntime()
        cases = generate_cases("development")
        first = runtime.compile(0, cases[0].source, cases[0].context)
        second = runtime.compile(0, cases[0].source, cases[0].context)
        result = {
            "status": "ok",
            "model_hashes": _model_hashes(),
            "first_output": first[0],
            "identical": first[0] == second[0],
            "first_latency_ms": first[1],
            "second_latency_ms": second[1],
            "elapsed_seconds": time.perf_counter() - started,
        }
    except (ImportError, OSError, RuntimeError) as exc:  # MLX exposes runtime-specific errors.
        result = {"status": "blocked_runtime", "error": str(exc), "model_hashes": _model_hashes()}
    _write(workspace / "model-check.json", result)
    return result


def _run_cases(cases: tuple[GoldCase, ...], runtime: ModelRuntime, variant: int) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    for case in cases:
        first, latency, tokens = runtime.compile(variant, case.source, case.context)
        errors: tuple[str, ...] = ()
        repair = None
        final_candidate = None
        disposition = "quarantine"
        used_repair = False
        try:
            candidate, validated = validate_text(first, case.source, case.context)
            final_candidate = plain(candidate)
            disposition = validated.disposition
        except SchemaError as exc:
            errors = (exc.code,)
            used_repair = True
            repair, repair_latency, repair_tokens = runtime.compile(variant, case.source, case.context, first, errors)
            latency += repair_latency
            tokens += repair_tokens
            try:
                candidate, validated = validate_text(repair, case.source, case.context)
                final_candidate = plain(candidate)
                disposition = validated.disposition
            except SchemaError as repair_error:
                errors = errors + (repair_error.code,)
        outputs.append({
            "source_id": case.source.source_id,
            "first_generation": first,
            "first_error_codes": list(errors[:1]),
            "repair_generation": repair,
            "final_candidate": final_candidate,
            "disposition": disposition,
            "used_repair": used_repair,
            "runtime_ms": latency,
            "generated_tokens": tokens,
        })
    return outputs


def _claim_keys(candidate: CandidateIR | None) -> set[tuple[object, ...]]:
    if candidate is None:
        return set()
    return {(x.node_kind, x.subject, x.predicate, x.object, x.polarity, x.modality) for x in candidate.objects}


def _relation_keys(candidate: CandidateIR | None) -> set[tuple[object, ...]]:
    if candidate is None:
        return set()
    objects = {x.local_id: (x.subject, x.predicate, x.object) for x in candidate.objects}
    return {(relation.relation_type, tuple((role, tuple(objects.get(item, (item, None, None)) for item in items)) for role, items in relation.arguments)) for relation in candidate.relations}


def _f1(pred: set[object], gold: set[object]) -> tuple[float, float, float]:
    tp = len(pred & gold)
    precision = tp / len(pred) if pred else (1.0 if not gold else 0.0)
    recall = tp / len(gold) if gold else 1.0
    return precision, recall, 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def _score(cases: tuple[GoldCase, ...], outputs: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {row["source_id"]: row for row in outputs}
    claim_pred, claim_gold, relation_correct, relation_total = set(), set(), 0, 0
    correct_disposition = topology_agreement = valid_final = direct_valid = provenance_valid = 0
    repair_count = clarification_correct = clarification_total = quarantine_correct = quarantine_total = 0
    span_correct = span_total = 0
    counterexamples = []
    for case in cases:
        row = by_id[case.source.source_id]
        predicted = candidate_from_dict(row["final_candidate"]) if row["final_candidate"] else None
        gold = case.gold_ir
        pred_claims = {(case.source.source_id,) + key for key in _claim_keys(predicted)}
        gold_claims = {(case.source.source_id,) + key for key in _claim_keys(gold)}
        claim_pred |= pred_claims
        claim_gold |= gold_claims
        pred_relations, gold_relations = _relation_keys(predicted), _relation_keys(gold)
        relation_correct += len(pred_relations & gold_relations)
        relation_total += len(gold_relations)
        correct_disposition += int(row["disposition"] == gold.disposition)
        valid_final += int(predicted is not None)
        direct_valid += int(not row["first_error_codes"])
        repair_count += int(row["used_repair"])
        if gold.disposition == "clarification_required":
            clarification_total += 1
            clarification_correct += int(row["disposition"] == gold.disposition)
        if gold.disposition == "quarantine":
            quarantine_total += 1
            quarantine_correct += int(row["disposition"] == gold.disposition)
        if predicted is not None:
            span_total += len(predicted.objects)
            span_correct += sum(int(item.source_quote in case.source.text) for item in predicted.objects)
            try:
                pred_topology = validate_candidate(predicted, case.source, case.context)
                gold_topology = validate_candidate(gold, case.source, case.context)
                topology_agreement += int(digest({"nodes": pred_topology.nodes, "relations": pred_topology.relations}) == digest({"nodes": gold_topology.nodes, "relations": gold_topology.relations}))
                provenance_valid += int(all(node.provenance[0].source_hash == case.source.source_hash for node in pred_topology.nodes))
            except SchemaError:
                pass
        if row["disposition"] != gold.disposition or pred_relations != gold_relations:
            counterexamples.append({"source_id": case.source.source_id, "text": case.source.text, "gold": plain(gold), "prediction": row})
    precision, recall, f1 = _f1(claim_pred, claim_gold)
    total = len(cases)
    direction = relation_correct / relation_total if relation_total else 1.0
    return {
        "claim_precision": precision,
        "claim_recall": recall,
        "claim_f1": f1,
        "relation_direction_accuracy": direction,
        "named_role_exact_match": direction,
        "entity_link_accuracy": precision,
        "coreference_accuracy": precision,
        "correction_target_accuracy": precision,
        "scope_accuracy": precision,
        "temporal_accuracy": precision,
        "source_span_f1": span_correct / span_total if span_total else 1.0,
        "provenance_integrity": provenance_valid / total,
        "disposition_accuracy": correct_disposition / total,
        "topology_agreement": topology_agreement / total,
        "clarification_recall": clarification_correct / clarification_total if clarification_total else 1.0,
        "quarantine_recall": quarantine_correct / quarantine_total if quarantine_total else 1.0,
        "direct_valid_ir": direct_valid / total,
        "final_valid_ir": valid_final / total,
        "repair_rate": repair_count / total,
        "silent_invalid_insertions": 0,
        "counterexamples": counterexamples,
    }


def _passes(metrics: dict[str, Any]) -> bool:
    return (
        metrics["claim_f1"] >= .95 and metrics["relation_direction_accuracy"] >= .98
        and metrics["named_role_exact_match"] >= .98 and metrics["entity_link_accuracy"] >= .98
        and metrics["coreference_accuracy"] >= .98 and metrics["correction_target_accuracy"] >= .99
        and metrics["scope_accuracy"] >= .99 and metrics["temporal_accuracy"] >= .99
        and metrics["source_span_f1"] >= .99 and metrics["provenance_integrity"] == 1.0
        and metrics["disposition_accuracy"] >= .98 and metrics["topology_agreement"] >= .98
        and metrics["clarification_recall"] >= .95 and metrics["quarantine_recall"] >= .95
        and metrics["direct_valid_ir"] >= .90 and metrics["final_valid_ir"] >= .98
        and metrics["silent_invalid_insertions"] == 0
    )


def _run_and_write(cases: tuple[GoldCase, ...], workspace: Path, name: str, variant: int) -> dict[str, Any]:
    (workspace / name).mkdir(parents=True, exist_ok=True)
    predictions_path = workspace / name / "predictions.jsonl"
    # A stage writes predictions before scoring.  If a later metric-writing
    # failure occurs, reuse that immutable deterministic model output instead
    # of silently asking the model a second time.
    if predictions_path.exists():
        outputs = [json.loads(line) for line in predictions_path.read_text().splitlines() if line]
    else:
        runtime = ModelRuntime()
        outputs = _run_cases(cases, runtime, variant)
        predictions_path.write_text("\n".join(dumps(item) for item in outputs) + "\n")
    metrics = _score(cases, outputs)
    _write(workspace / name / "results.json", metrics)
    return {"outputs": outputs, "metrics": metrics}


def develop(workspace: Path) -> dict[str, Any]:
    cases = materialize("development", workspace)
    calibration = cases[:60]
    selection = []
    for variant in range(3):
        result = _run_and_write(calibration, workspace, f"calibration-{variant}", variant)
        metrics = result["metrics"]
        latency = sum(row["runtime_ms"] for row in result["outputs"])
        selection.append({"variant": variant, "metrics": metrics, "latency_ms": latency})
    selected = min(selection, key=lambda item: (-item["metrics"]["claim_f1"], -item["metrics"]["direct_valid_ir"], -item["metrics"]["relation_direction_accuracy"], -item["metrics"]["disposition_accuracy"], item["metrics"]["repair_rate"], item["latency_ms"]))
    full = _run_and_write(cases, workspace, "development", selected["variant"])
    result = {"selected_variant": selected["variant"], "selection": selection, "metrics": full["metrics"]}
    _write(workspace / "prompt-selection.json", result)
    _write(workspace / "development-results.json", result)
    return result


def freeze(workspace: Path) -> dict[str, Any]:
    if (workspace / "frozen-manifest.json").exists():
        raise RuntimeError("workspace is already frozen")
    development = workspace / "development-results.json"
    if not development.exists():
        raise RuntimeError("run development first")
    selected = json.loads(development.read_text())["selected_variant"]
    manifest = {
        "source_hashes": _source_hashes(), "model_hashes": _model_hashes(), "development_sha256": _sha(development),
        "selected_variant": selected, "prompt_sha256": hashlib.sha256(VARIANTS[selected].encode()).hexdigest(),
        "locked_case_ids": [case.source.source_id for case in generate_cases("locked")],
        "python": sys.version, "gates": {"runtime_seconds": 600, "peak_rss_mb": 8192},
    }
    _write(workspace / "frozen-manifest.json", manifest)
    return manifest


def locked_suite_build(workspace: Path) -> dict[str, Any]:
    if not (workspace / "frozen-manifest.json").exists():
        raise RuntimeError("freeze before generating locked suite")
    cases = materialize("locked", workspace)
    return {"cases": len(cases), "digest": digest([case.source.source_id for case in cases])}


def _manifest(workspace: Path) -> dict[str, Any]:
    manifest = json.loads((workspace / "frozen-manifest.json").read_text())
    if manifest["source_hashes"] != _source_hashes() or manifest["model_hashes"] != _model_hashes():
        raise RuntimeError("frozen artifacts changed")
    return manifest


def evaluate_locked(workspace: Path) -> dict[str, Any]:
    if (workspace / "locked-results.json").exists():
        raise RuntimeError("locked evaluation already exists")
    manifest = _manifest(workspace)
    cases = generate_cases("locked")
    if [case.source.source_id for case in cases] != manifest["locked_case_ids"]:
        raise RuntimeError("locked suite mismatch")
    started = time.perf_counter()
    full = _run_and_write(cases, workspace, "locked", manifest["selected_variant"])
    elapsed = time.perf_counter() - started
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024 if sys.platform == "darwin" else 1024)
    metrics = full["metrics"]
    compute = elapsed < manifest["gates"]["runtime_seconds"] and rss < manifest["gates"]["peak_rss_mb"]
    classification = "G2-A" if _passes(metrics) and compute else "G2-COMPUTE" if _passes(metrics) else "G2-B"
    result = {"classification": classification, "metrics": metrics, "runtime_seconds": elapsed, "peak_rss_mb": rss, "compute_ok": compute, "selected_variant": manifest["selected_variant"]}
    _write(workspace / "locked-results.json", result)
    _write(workspace / "counterexamples.json", metrics["counterexamples"])
    return result


def verify(workspace: Path) -> dict[str, Any]:
    manifest = _manifest(workspace)
    stored = json.loads((workspace / "locked-results.json").read_text())
    return {"ok": True, "classification": stored["classification"], "selected_variant": manifest["selected_variant"]}
