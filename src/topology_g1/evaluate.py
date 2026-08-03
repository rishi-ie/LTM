from __future__ import annotations

import hashlib
import json
import resource
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from .codec import decode_node, decode_relation, digest, encode_node, encode_relation
from .engine import execute, verify_derivation
from .fixtures import Fixture, fixtures, legacy_node_v1
from .migrate import node_v1_to_v2
from .registry import REGISTRY, validate_relation
from .schemas import SchemaError
from .store import TopologyStore

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "topology-g1.json"
LOCKED_SPLIT = "locked-final"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_hashes() -> dict[str, str]:
    package = Path(__file__).resolve().parent
    paths = sorted(package.glob("*.py")) + [CONFIG]
    return {str(path.relative_to(ROOT)): _sha(path) for path in paths}


def _write(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def _expected_event(fixture: Fixture, derivations, contribution, state) -> bool:
    r = fixture.relation.relation_type
    if fixture.expected == "derive":
        premises = fixture.relation.role_ids("premise")
        should_derive = fixture.state.scope_id == fixture.relation.scope_id and all(item in fixture.state.active_claims for item in premises)
        if r == "equals":
            left, right = fixture.relation.role_ids("left")[0], fixture.relation.role_ids("right")[0]
            should_derive = fixture.state.value(left) == fixture.state.value(right)
        return bool(derivations) == should_derive
    if fixture.expected == "obligation":
        return bool(contribution.hard_obligations) == (fixture.relation.role_ids("dependent")[0] in fixture.state.active_claims and fixture.relation.role_ids("prerequisite")[0] not in fixture.state.active_claims)
    if fixture.expected == "conflict":
        return bool(state.conflicts) == all(item in fixture.state.active_claims for item in fixture.relation.role_ids("left") + fixture.relation.role_ids("right"))
    if fixture.expected == "temporal":
        return bool(contribution.hard_obligations) == (contribution.residual > 0)
    if fixture.expected == "supersede":
        older = fixture.relation.role_ids("older")[0]
        newer = fixture.relation.role_ids("newer")[0]
        return (older in state.inactive_claims) == (newer in fixture.state.active_claims)
    if fixture.expected == "message":
        return len(contribution.messages) == 1 and contribution.messages[0].relation_id == fixture.relation.relation_id
    if fixture.expected == "preference":
        return fixture.relation.role_ids("preference")[0] in state.response_constraints
    if fixture.expected == "reference":
        return (fixture.relation.role_ids("mention")[0], fixture.relation.role_ids("entity")[0]) in state.reference_bindings
    if fixture.expected == "scope":
        return not contribution.hard_obligations
    return False


def _field_contracts(results: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    required = {"implies", "conjoins", "requires", "excludes", "equals", "before", "fictional_rule"}
    failures = []
    for relation_type in sorted(required):
        values = [row["residual"] for row in results if row["relation_type"] == relation_type and row["valid"]]
        if not values or not any(value == 0.0 for value in values) or not any(value > 0.0 for value in values):
            failures.append(f"field contract missing satisfied/violated {relation_type}")
    return not failures, failures


def run_suite(items: tuple[Fixture, ...], workdir: Path) -> dict[str, Any]:
    workdir.mkdir(parents=True, exist_ok=True)
    store_path = workdir / "topology.sqlite"
    if store_path.exists():
        store_path.unlink()
    store = TopologyStore(store_path)
    rows: list[dict[str, Any]] = []
    checks = {
        "valid_acceptance": 0,
        "valid_total": 0,
        "invalid_rejection": 0,
        "invalid_total": 0,
        "round_trip": 0,
        "operator": 0,
        "verifier": 0,
        "adversarial_rejection": 0,
        "migration": 0,
    }
    try:
        for fixture in items:
            nodes = {node.node_id: node for node in fixture.nodes}
            row: dict[str, Any] = {
                "fixture_id": fixture.fixture_id,
                "family": fixture.family,
                "variant": fixture.variant,
                "valid": fixture.invalid_code is None,
                "relation_type": fixture.relation.relation_type,
                "residual": None,
                "passed": False,
                "error": None,
            }
            try:
                validate_relation(fixture.relation, nodes)
                if fixture.invalid_code is not None:
                    checks["invalid_total"] += 1
                    row["error"] = "INVALID_ACCEPTED"
                    store.quarantine("INVALID_ACCEPTED", fixture.fixture_id)
                    rows.append(row)
                    continue
                checks["valid_total"] += 1
                if all(decode_node(encode_node(node)) == node for node in nodes.values()) and decode_relation(encode_relation(fixture.relation)) == fixture.relation:
                    checks["round_trip"] += 1
                for node in nodes.values():
                    store.insert_node(node)
                store.insert_relation(fixture.relation)
                derivations, contribution, updated = execute(fixture.relation, nodes, fixture.state)
                row["residual"] = contribution.residual
                operator_ok = _expected_event(fixture, derivations, contribution, updated)
                checks["operator"] += int(operator_ok)
                verifier_ok = True
                adversarial_ok = True
                for derivation in derivations:
                    verifier_ok = verifier_ok and verify_derivation(derivation, fixture.relation, nodes, fixture.state).valid
                    fabricated = derivation.__class__(
                        fixture.relation.role_ids("premise")[0] if fixture.relation.role_ids("premise") else derivation.conclusion_id,
                        derivation.relation_id,
                        (),
                        derivation.scope_id,
                        derivation.provenance,
                    )
                    adversarial_ok = adversarial_ok and not verify_derivation(fabricated, fixture.relation, nodes, fixture.state).valid
                checks["verifier"] += int(verifier_ok)
                checks["adversarial_rejection"] += int(adversarial_ok)
                migration_ok = True
                if fixture.migration:
                    migrated = node_v1_to_v2(legacy_node_v1(fixture.nodes[0]))
                    migration_ok = migrated == fixture.nodes[0]
                    checks["migration"] += int(migration_ok)
                checks["valid_acceptance"] += 1
                row["passed"] = operator_ok and verifier_ok and adversarial_ok and migration_ok
            except SchemaError as exc:
                row["error"] = exc.code
                if fixture.invalid_code is not None:
                    checks["invalid_total"] += 1
                    checks["invalid_rejection"] += int(exc.code == fixture.invalid_code)
                    row["passed"] = exc.code == fixture.invalid_code
                    store.quarantine(exc.code, fixture.fixture_id)
            rows.append(row)
        snapshot = store.snapshot_hash()
        reopened = TopologyStore(store_path)
        reopened_hash = reopened.snapshot_hash()
        reopened.close()
        replay_path = workdir / "replay.sqlite"
        replay = store.replay(replay_path)
        replay_hash = replay.snapshot_hash()
        replay.close()
        reverse_path = workdir / "reverse.sqlite"
        reverse = TopologyStore(reverse_path)
        for node in sorted(store.nodes().values(), key=lambda item: item.node_id, reverse=True):
            reverse.insert_node(node)
        for relation in sorted(store.relations().values(), key=lambda item: item.relation_id, reverse=True):
            reverse.insert_relation(relation)
        reverse_hash = reverse.snapshot_hash()
        reverse.close()
    finally:
        store.close()
    field_ok, field_failures = _field_contracts(rows)
    total_valid = checks["valid_total"]
    total_invalid = checks["invalid_total"]
    passed = (
        checks["valid_acceptance"] == total_valid
        and checks["invalid_rejection"] == total_invalid
        and checks["round_trip"] == total_valid
        and checks["operator"] == total_valid
        and checks["verifier"] == total_valid
        and checks["adversarial_rejection"] == total_valid
        and checks["migration"] == sum(item.migration for item in items)
        and field_ok
        and snapshot == reopened_hash == replay_hash == reverse_hash
        and all(row["passed"] for row in rows)
    )
    return {
        "passed": passed,
        "checks": checks,
        "field_contract_ok": field_ok,
        "field_contract_failures": field_failures,
        "snapshot_hash": snapshot,
        "reopened_hash": reopened_hash,
        "replay_hash": replay_hash,
        "reverse_hash": reverse_hash,
        "rows": rows,
    }


def develop(workspace: Path) -> dict[str, Any]:
    workspace.mkdir(parents=True, exist_ok=True)
    result = run_suite(fixtures("development"), workspace / "development")
    _write(workspace / "development-results.json", result)
    return result


def freeze(workspace: Path) -> dict[str, Any]:
    development = workspace / "development-results.json"
    if not development.exists():
        raise RuntimeError("run develop before freeze")
    if (workspace / "frozen-manifest.json").exists():
        raise RuntimeError("workspace already frozen")
    report = json.loads(development.read_text())
    if not report["passed"]:
        raise RuntimeError("development failed; freezing is refused")
    manifest = {
        "source_hashes": _source_hashes(),
        "development_sha256": _sha(development),
        "locked_fixture_digest": digest([item.fixture_id for item in fixtures(LOCKED_SPLIT)]),
        "registry_digest": digest({key: value for key, value in REGISTRY.items()}),
        "python": sys.version,
        "sqlite": __import__("sqlite3").sqlite_version,
        "gates": {"runtime_seconds": 10, "peak_rss_mb": 200},
    }
    _write(workspace / "frozen-manifest.json", manifest)
    return manifest


def _verify_manifest(workspace: Path) -> dict[str, Any]:
    manifest = json.loads((workspace / "frozen-manifest.json").read_text())
    if manifest["source_hashes"] != _source_hashes():
        raise RuntimeError("frozen source hashes do not match")
    if manifest["locked_fixture_digest"] != digest([item.fixture_id for item in fixtures(LOCKED_SPLIT)]):
        raise RuntimeError("locked fixture digest does not match")
    return manifest


def evaluate_locked(workspace: Path) -> dict[str, Any]:
    if (workspace / "locked-results.json").exists():
        raise RuntimeError("locked evaluation already exists")
    manifest = _verify_manifest(workspace)
    started = time.perf_counter()
    result = run_suite(fixtures(LOCKED_SPLIT), workspace / "locked")
    elapsed = time.perf_counter() - started
    rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024 if sys.platform == "darwin" else 1024)
    result["runtime_seconds"] = elapsed
    result["peak_rss_mb"] = rss_mb
    result["compute_ok"] = elapsed < manifest["gates"]["runtime_seconds"] and rss_mb < manifest["gates"]["peak_rss_mb"]
    result["classification"] = "G1-A" if result["passed"] and result["compute_ok"] else "G1-COMPUTE" if result["passed"] else "G1-C"
    _write(workspace / "locked-results.json", result)
    return result


def verify(workspace: Path) -> dict[str, Any]:
    manifest = _verify_manifest(workspace)
    stored = json.loads((workspace / "locked-results.json").read_text())
    with tempfile.TemporaryDirectory() as temp:
        rerun = run_suite(fixtures(LOCKED_SPLIT), Path(temp))
    equal = all(stored[key] == rerun[key] for key in ("passed", "checks", "field_contract_ok", "snapshot_hash", "replay_hash", "reverse_hash"))
    return {"ok": equal, "manifest": bool(manifest), "classification": stored["classification"]}
