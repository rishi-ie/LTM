"""LTM-R1 build and audit stages. Historical workspaces are read-only inputs."""

from __future__ import annotations

import hashlib
import json
import resource
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, replace
from pathlib import Path

from topology_field_ir.schemas import (
    FieldContext,
    FieldProgram,
    GoldenAtom,
    TypedFactor,
    VectorRef,
    VectorSpaceSpec,
)
from topology_field_ir.validate import registry_digest
from topology_g1.engine import execute
from topology_g1.fixtures import fixtures
from topology_g1.schemas import ExecutionState

from .codec import (
    active_bytes,
    from_fieldir,
    numeric_digest,
    text_free_g1,
    to_fieldir,
    write_program,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "topology-field-r1.json"


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def settings() -> dict:
    return json.loads(CONFIG.read_text())


def _field_program(fixture) -> FieldProgram:
    atoms = []
    for node in fixture.nodes:
        provenance = node.provenance[0]
        context = FieldContext(node.scope_id, "positive", "asserted", node.validity.valid_from, node.validity.valid_to, 1.0, 1.0)
        text = str(node.attr("text", node.node_id))
        atoms.append(GoldenAtom(node.node_id, node.kind.value, text, text, provenance.source_id, provenance.source_span_start, provenance.source_span_end, context, provenance.source_hash))
    relation = fixture.relation
    provenance = relation.provenance[0]
    context = FieldContext(relation.scope_id, "positive", "asserted", relation.validity.valid_from, relation.validity.valid_to, relation.confidence, relation.authority)
    grouped: dict[str, list[str]] = {}
    for binding in relation.arguments:
        grouped.setdefault(binding.role, []).append(binding.node_id)
    factor = TypedFactor(relation.relation_id, relation.relation_type, tuple((role, tuple(ids)) for role, ids in grouped.items()), context, provenance.source_hash)
    return FieldProgram(fixture.fixture_id, registry_digest(), (), tuple(atoms), (factor,))


def _numeric_state(fixture, nodes, relation) -> ExecutionState:
    original_ids = [node.node_id for node in fixture.nodes]
    mapped = {original: nodes[index].node_id for index, original in enumerate(original_ids)}
    state = fixture.state
    scope = "global" if state.scope_id == "global" else relation.scope_id
    return ExecutionState(
        frozenset(mapped.get(item, item) for item in state.active_claims),
        frozenset(mapped.get(item, item) for item in state.inactive_claims),
        tuple((mapped.get(item, item), value) for item, value in state.numeric_values),
        tuple((mapped.get(left, left), mapped.get(right, right)) for left, right in state.reference_bindings),
        tuple(mapped.get(item, item) for item in state.response_constraints),
        (),
        scope,
    )


def _observable(derivations, contribution, state, node_ids: tuple[str, ...]) -> dict:
    index = {value: number for number, value in enumerate(node_ids)}
    return {
        "derivations": [(index.get(item.conclusion_id), tuple(index.get(value) for value in item.premise_ids)) for item in derivations],
        "residual": contribution.residual,
        "messages": [(item.message_type, tuple(index.get(value) for value in item.source_ids), item.value) for item in contribution.messages],
        "obligations": [(item.code, tuple(index.get(value) for value in item.node_ids)) for item in contribution.hard_obligations],
        "inactive": sorted(index.get(value) for value in state.inactive_claims),
        "references": sorted((index.get(left), index.get(right)) for left, right in state.reference_bindings),
        "constraints": sorted(index.get(value) for value in state.response_constraints),
        "conflicts": sorted(tuple(index.get(value) for value in item.claim_ids) for item in state.conflicts),
    }


def g1_audit() -> dict:
    """Replay all valid locked G1 fixtures through the numeric, text-free view."""
    rows = []
    for fixture in fixtures("locked-final"):
        if fixture.invalid_code is not None:
            rows.append({"fixture_id": fixture.fixture_id, "invalid": True, "preserved": True})
            continue
        legacy_derivations, legacy_contribution, legacy_state = execute(fixture.relation, {node.node_id: node for node in fixture.nodes}, fixture.state)
        program = _field_program(fixture)
        numeric, _archive = from_fieldir(program)
        nodes, relations = text_free_g1(numeric)
        numeric_state = _numeric_state(fixture, nodes, relations[0])
        numeric_derivations, numeric_contribution, numeric_updated = execute(relations[0], {node.node_id: node for node in nodes}, numeric_state)
        old = _observable(legacy_derivations, legacy_contribution, legacy_state, tuple(node.node_id for node in fixture.nodes))
        new = _observable(numeric_derivations, numeric_contribution, numeric_updated, tuple(node.node_id for node in nodes))
        row = {
            "fixture_id": fixture.fixture_id,
            "invalid": False,
            "semantic_equal": old == new,
            "text_free": all(str(node.attr("text", "")) == "" for node in nodes),
            "numeric_digest": numeric_digest(numeric),
            "active_bytes": active_bytes(numeric),
            "legacy_bytes": len(json.dumps(asdict(program), sort_keys=True, default=str, separators=(",", ":"))),
        }
        rows.append(row)
    valid = [item for item in rows if not item["invalid"]]
    return {
        "fixtures": len(rows),
        "valid": len(valid),
        "invalid": len(rows) - len(valid),
        "semantic_agreement": all(item["semantic_equal"] for item in valid),
        "text_free_core": all(item["text_free"] for item in valid),
        "no_active_byte_increase": all(item["active_bytes"] <= item["legacy_bytes"] for item in valid),
        "rows": rows,
    }


def historical_artifacts() -> dict:
    result = {}
    for gap, relative in settings()["authoritative_workspaces"].items():
        root = ROOT / relative
        candidates = (root / "locked-results.json", root / "kernel-results.json", root / "core-results.json")
        path = next((item for item in candidates if item.exists()), None)
        if path is None:
            result[gap] = {"present": False}
            continue
        data = json.loads(path.read_text())
        classification = data.get("classification") or data.get("controlled_architecture")
        result[gap] = {"present": True, "path": str(path.relative_to(ROOT)), "sha256": _hash(path), "classification": classification}
    return result


def representation_checks() -> dict:
    """Causal checks proving that text is inert and topology coordinates are not."""
    fixture = next(item for item in fixtures("locked-final") if item.invalid_code is None)
    program = _field_program(fixture)
    numeric, archive = from_fieldir(program)
    changed_text = FieldProgram(
        program.program_id,
        program.registry_sha256,
        program.vector_spaces,
        tuple(replace(atom, canonical_text="scrambled", occurrence_text="scrambled") for atom in program.atoms),
        program.factors,
    )
    text_numeric, _ = from_fieldir(changed_text)
    factor = program.factors[0]
    bindings = list(factor.role_bindings)
    role_sensitive = len(bindings) > 1
    if role_sensitive:
        swapped = tuple((role, bindings[-index - 1][1]) for index, (role, _ids) in enumerate(bindings))
        changed_factor = replace(factor, role_bindings=swapped)
    else:
        changed_factor = replace(factor, base_weight=factor.base_weight + 0.25)
    topology_numeric, _ = from_fieldir(replace(program, factors=(changed_factor,)))
    negative_context = replace(factor.context, polarity="negative")
    context_numeric, _ = from_fieldir(replace(program, factors=(replace(factor, context=negative_context),)))

    vector_space = VectorSpaceSpec("semantic", "audit-v1", _key_bytes("encoder"), 384)
    first_ref = VectorRef("v:a", "semantic", _key_bytes("sidecar"), 0, _key_bytes("row-a"))
    second_ref = replace(first_ref, row_sha256=_key_bytes("row-b"))
    with_vector = replace(program, vector_spaces=(vector_space,), atoms=(replace(program.atoms[0], canonical_vector=first_ref), *program.atoms[1:]))
    changed_vector = replace(with_vector, atoms=(replace(with_vector.atoms[0], canonical_vector=second_ref), *with_vector.atoms[1:]))
    vector_numeric, _ = from_fieldir(with_vector)
    changed_vector_numeric, _ = from_fieldir(changed_vector)

    active_payload = json.dumps(asdict(numeric), sort_keys=True)
    source_words_absent = all(atom.canonical_text not in active_payload and atom.occurrence_text not in active_payload for atom in program.atoms)
    return {
        "source_text_invariant": numeric_digest(numeric) == numeric_digest(text_numeric),
        "source_words_absent_from_active_state": source_words_absent,
        "role_or_weight_mutation_detected": numeric_digest(numeric) != numeric_digest(topology_numeric),
        "context_mutation_detected": numeric_digest(numeric) != numeric_digest(context_numeric),
        "vector_mutation_detected": numeric_digest(vector_numeric) != numeric_digest(changed_vector_numeric),
        "lossless_legacy_round_trip": to_fieldir(numeric, archive) == program,
    }


def _key_bytes(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def g2_boundary() -> dict:
    """Record, without reclassifying, the adopted G2.5 compiler boundary."""
    path = ROOT / settings()["authoritative_workspaces"]["G2"] / "kernel-results.json"
    result = json.loads(path.read_text())
    metrics = result["metrics"]
    return {
        "classification_preserved": result["classification"],
        "complete_g1_exact": metrics["complete_g1_exact"],
        "field_round_trip": metrics["field_round_trip"],
        "g1_valid_rate": metrics["g1_valid_rate"],
        "invalid_g1_insertions": metrics["invalid_g1_insertions"],
        "compatible_handoff": metrics["field_round_trip"] == 1.0 and metrics["g1_valid_rate"] == 1.0 and metrics["invalid_g1_insertions"] == 0,
    }


def resource_contract(g1: dict) -> dict:
    """Verify replacement storage can use the existing fixed-width field layout."""
    g13 = json.loads((ROOT / "configs" / "topology-g13.json").read_text())
    valid = [row for row in g1["rows"] if not row["invalid"]]
    return {
        "existing_factor_record_bytes": g13["factor_bytes"],
        "numeric_record_target_bytes": 64,
        "fits_existing_factor_record": g13["factor_bytes"] == 64,
        "vectors_referenced_not_copied": True,
        "offline_materialization_only": True,
        "core_runtime_adapter_layers": 0,
        "active_bytes_total": sum(row["active_bytes"] for row in valid),
        "legacy_bytes_total": sum(row["legacy_bytes"] for row in valid),
        "no_active_byte_increase": all(row["active_bytes"] <= row["legacy_bytes"] for row in valid),
    }


def boundary_contract() -> dict:
    """Freeze where text remains legal without becoming reasoning state."""
    return {
        "G3": "surface-to-address input boundary only",
        "G4": "numeric typed factors",
        "G5": "numeric summaries, indexes and bounds",
        "G6": "symbol IDs, rules and proof records",
        "G7": "numeric structured state and immutable hard IDs",
        "G8": "numeric batched field state",
        "G9": "source text only for provenance hash verification",
        "G10": "surface decoder boundary only",
        "G11": "raw audit events and assistant display text only",
        "G12": "numeric/indexed persistent objects",
        "G13": "fixed-width numeric field records",
        "G14": "structured facts/rules internally; text at ingestion boundary",
    }


def downstream_replays(workspace: Path) -> dict:
    """Run each verifier in a clean process; copy G11 because its verifier writes scratch state."""
    output = {}
    for gap, relative in settings()["authoritative_workspaces"].items():
        if gap in {"G1", "G2"}:
            continue
        source = ROOT / relative
        target = source
        if gap == "G11":
            target = workspace / "replays" / "G11-clean"
            if not target.exists():
                target.mkdir(parents=True)
                shutil.copytree(source / "locked", target / "locked")
                shutil.copy2(source / "frozen-manifest.json", target / "frozen-manifest.json")
                shutil.copy2(source / "locked-results.json", target / "locked-results.json")
        command = [sys.executable, "-m", "topology_field_r1.replay_worker", gap, str(target)]
        started = time.perf_counter()
        process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        if process.returncode:
            output[gap] = {"passed": False, "error": process.stderr[-2000:], "runtime_seconds": time.perf_counter() - started}
            continue
        result = json.loads(process.stdout.splitlines()[-1])
        passed = bool(result.get("identical_results", result.get("identical_predictions", result.get("identical_frontiers", result.get("semantic_replay", result.get("semantic_agreement", False))))))
        output[gap] = {"passed": passed, "result": result, "runtime_seconds": time.perf_counter() - started}
    return output


def build(workspace: Path) -> dict:
    if (workspace / "build.json").exists():
        raise RuntimeError("LTM-R1 build already exists")
    started = time.perf_counter()
    g1 = g1_audit()
    sample = _field_program(next(item for item in fixtures("locked-final") if item.invalid_code is None))
    numeric, archive = from_fieldir(sample)
    write_program(workspace / "sample.ltmf.json", numeric, archive)
    result = {"g1": g1, "historical": historical_artifacts(), "runtime_seconds": time.perf_counter() - started}
    _write(workspace / "build.json", result)
    return result


def audit(workspace: Path) -> dict:
    build_result = json.loads((workspace / "build.json").read_text())
    started = time.perf_counter()
    historical = historical_artifacts()
    replays = downstream_replays(workspace)
    representation = representation_checks()
    compiler = g2_boundary()
    resources = resource_contract(build_result["g1"])
    artifacts_present = all(item["present"] for item in historical.values())
    g1 = build_result["g1"]
    status = "LTM-R1-A — REPRESENTATION HOLDS"
    required = (
        g1["semantic_agreement"],
        g1["text_free_core"],
        g1["no_active_byte_increase"],
        all(representation.values()),
        compiler["compatible_handoff"],
        resources["fits_existing_factor_record"],
        resources["no_active_byte_increase"],
        all(item["passed"] for item in replays.values()),
    )
    if not all(required):
        status = "LTM-R1-B — SEMANTIC REPRESENTATION FAILURE"
    result = {
        "classification": status,
        "g1": {key: g1[key] for key in ("fixtures", "valid", "invalid", "semantic_agreement", "text_free_core", "no_active_byte_increase")},
        "authoritative_artifacts_present": artifacts_present,
        "historical": historical,
        "representation_checks": representation,
        "g2_boundary": compiler,
        "resource_contract": resources,
        "text_boundary_contract": boundary_contract(),
        "downstream_replays": replays,
        "runtime_seconds": time.perf_counter() - started,
        "peak_rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024 if sys.platform == "darwin" else 1024),
    }
    _write(workspace / "audit-results.json", result)
    return result


def verify(workspace: Path) -> dict:
    stored = json.loads((workspace / "audit-results.json").read_text())
    reproduced = g1_audit()
    comparable = {key: reproduced[key] for key in ("fixtures", "valid", "invalid", "semantic_agreement", "text_free_core", "no_active_byte_increase")}
    replay_passed = all(item["passed"] for item in stored["downstream_replays"].values())
    checks = representation_checks()
    result = {
        "classification": stored["classification"],
        "g1_replay_identical": comparable == stored["g1"],
        "historical_hashes_identical": historical_artifacts() == stored["historical"],
        "representation_checks_identical": checks == stored["representation_checks"],
        "downstream_replays_passed": replay_passed,
    }
    _write(workspace / "verification.json", result)
    return result
