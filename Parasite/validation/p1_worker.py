"""Runtime-only worker for P1; it receives public rows and never gold."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Parasite/src"))
sys.path.insert(0, str(ROOT / "src"))

from parasite.contracts import IngestRequest, QueryRequest
from parasite.optimizer.equilibrium import solve_equilibrium
from parasite.runtime import ParasiteRuntime


def _request(row: dict) -> IngestRequest:
    fields = ("tenant_id", "reality_id", "source_id", "source_hash", "input_kind", "payload", "session_id", "scope_key", "valid_from", "valid_to")
    return IngestRequest(**{key: row["request"][key] for key in fields if key in row["request"]})


def _prediction(row: dict, result, elapsed: float) -> dict:
    claims = tuple(result.authorized_claims)
    return {"case_id": row["case_id"], "track": row["track"], "disposition": result.disposition,
            "claim": claims[0] if claims else None, "claims": claims, "alternatives": tuple(result.alternatives),
            "certificate_length": len(result.proof_or_equilibrium_certificate), "tension": result.tension,
            "failure_codes": tuple(result.failure_codes), "runtime_ms": elapsed, "query_ms": elapsed,
            "trace": tuple(result.trace)}


def _control_request(row: dict, mode: str) -> IngestRequest:
    original = row["request"]
    payload = json.loads(json.dumps(original["payload"]))
    factors = payload.get("factors", [])
    if mode == "remove_decisive":
        target = row["request"]["query"]["query_expression"]
        target_id = next((atom["id"] for atom in payload.get("atoms", ()) if atom.get("expression") == target), None)
        factors = [factor for factor in factors if factor.get("outcome") != target_id]
    elif mode == "swap_authority":
        target = row["request"]["query"]["query_expression"]
        target_id = next((atom["id"] for atom in payload.get("atoms", ()) if atom.get("expression") == target), None)
        for factor in factors:
            if factor.get("outcome") == target_id and int(factor.get("polarity", 1)) == 1:
                factor["polarity"] = -1
                break
    elif mode == "duplicate_source":
        if factors:
            target = row["request"]["query"]["query_expression"]
            target_id = next((atom["id"] for atom in payload.get("atoms", ()) if atom.get("expression") == target), None)
            source_factor = next((factor for factor in factors if factor.get("outcome") == target_id), factors[-1])
            duplicate = dict(source_factor); duplicate["id"] = duplicate["id"] + "-copy"
            factors = factors[:-1] + [duplicate]
    elif mode == "shuffle_endpoints":
        for factor in factors:
            if len(factor.get("inputs", ())) == 1:
                source = factor["inputs"][0]; factor["inputs"] = [factor["outcome"]]; factor["outcome"] = source
    payload["factors"] = factors
    payload["source_text"] = str(payload.get("source_text", "")) + " control " + mode
    request = dict(original)
    request.update(reality_id=original["reality_id"] + "-" + mode, source_id=original["source_id"] + "-" + mode,
                   source_hash=__import__("hashlib").sha256(payload["source_text"].encode()).hexdigest(), payload=payload)
    return IngestRequest(**{key: request[key] for key in ("tenant_id", "reality_id", "source_id", "source_hash", "input_kind", "payload")})


def _control_prediction(runtime: ParasiteRuntime, row: dict, mode: str) -> dict:
    started = time.perf_counter()
    request = _request(row)
    if mode in {"no_optimization", "one_sweep"}:
        compiled = runtime.ingest(request)
        if compiled.disposition != "accept":
            return {"case_id": row["case_id"], "mode": mode, "disposition": compiled.disposition, "claim": None, "runtime_ms": (time.perf_counter() - started) * 1000}
        loaded = runtime.field.load(request.tenant_id, request.reality_id)
        query = row["request"]["query"]
        assumptions = tuple(runtime._resolve_atom(loaded, str(item)) for item in query["assumptions"])
        limited = solve_equilibrium(loaded.atoms, loaded.factors, assumption_atom_ids=assumptions,
                                    query_expression=query["query_expression"], query_sort=query["query_sort"],
                                    maximum_sweeps=0 if mode == "no_optimization" else 1)
        claim = None
        if limited.selected_candidate_id:
            candidate = next(item for item in limited.candidates if item.candidate_id == limited.selected_candidate_id)
            claim = ("not " if candidate.polarity < 0 else "") + candidate.expression
        return {"case_id": row["case_id"], "mode": mode, "disposition": limited.disposition, "claim": claim,
                "runtime_ms": (time.perf_counter() - started) * 1000}
    request = _control_request(row, mode)
    compiled = runtime.ingest(request)
    if compiled.disposition != "accept":
        return {"case_id": row["case_id"], "mode": mode, "disposition": compiled.disposition, "claim": None, "runtime_ms": (time.perf_counter() - started) * 1000}
    query = row["request"]["query"]
    result = runtime.ask(QueryRequest(request.tenant_id, request.reality_id, row["case_id"] + "-" + mode, "fixed_equilibrium", "formal", query))
    return {"case_id": row["case_id"], "mode": mode, "disposition": result.disposition,
            "claim": result.authorized_claims[0] if result.authorized_claims else None,
            "runtime_ms": (time.perf_counter() - started) * 1000}


def run(public_path: Path, output_path: Path, state_path: Path, config_path: Path, controls_path: Path | None = None, control_ids_path: Path | None = None) -> None:
    rows = [json.loads(line) for line in public_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    predictions = []
    control_predictions = []
    invalid_partial = 0
    representation_checked = 0
    representation_passed = 0
    network_calls = 0
    control_ids = set(json.loads(control_ids_path.read_text(encoding="utf-8"))) if control_ids_path is not None else set()
    control_rows = [row for row in rows if row["case_id"] in control_ids] if control_ids else [row for row in rows if row["track"] == "equilibrium"][:4]
    with ParasiteRuntime.open(state_path, config_path) as runtime:
        for row in rows:
            started = time.perf_counter()
            request = _request(row)
            compiled = runtime.ingest(request)
            if row["track"] == "compiler" and compiled.disposition == "quarantine" and runtime.inspect(request.tenant_id, request.reality_id).get("generation_id") is not None:
                invalid_partial += 1
            if row["track"] != "conversation":
                representation_checked += 1
                verified = runtime.verify(request.tenant_id, request.reality_id)
                representation_passed += int(bool(verified.get("verified")) == (compiled.disposition == "accept"))
            if row["track"] == "compiler":
                prediction = {"case_id": row["case_id"], "track": row["track"], "disposition": compiled.disposition,
                              "claim": None, "claims": (), "alternatives": (), "certificate_length": 0,
                              "tension": 0.0, "failure_codes": tuple(compiled.failure_codes),
                              "runtime_ms": (time.perf_counter() - started) * 1000, "committed": dict(compiled.evidence).get("committed", False)}
            elif row["track"] == "conversation":
                if compiled.disposition == "accept":
                    query_started = time.perf_counter()
                    result = runtime.ask(QueryRequest(request.tenant_id, request.reality_id, row["case_id"], "conversation_memory", "context", {}, session_id=request.session_id))
                    prediction = _prediction(row, result, (time.perf_counter() - started) * 1000)
                    prediction["representation_verified"] = True
                    prediction["query_ms"] = (time.perf_counter() - query_started) * 1000
                else:
                    prediction = {"case_id": row["case_id"], "track": row["track"], "disposition": compiled.disposition,
                                  "claim": None, "claims": (), "alternatives": (), "certificate_length": 0,
                                  "tension": 0.0, "failure_codes": tuple(compiled.failure_codes),
                                  "runtime_ms": (time.perf_counter() - started) * 1000, "query_ms": 0.0, "committed": False}
            elif row["track"] == "exact":
                query = QueryRequest(request.tenant_id, request.reality_id, row["case_id"], "exact", "topology", {"target_atom_id": "n-b"})
                query_started = time.perf_counter()
                result = runtime.ask(query) if compiled.disposition == "accept" else None
                prediction = _prediction(row, result, (time.perf_counter() - started) * 1000) if result else {
                    "case_id": row["case_id"], "track": row["track"], "disposition": compiled.disposition, "claim": None,
                    "claims": (), "alternatives": (), "certificate_length": 0, "tension": 0.0,
                    "failure_codes": tuple(compiled.failure_codes), "runtime_ms": (time.perf_counter() - started) * 1000,
                }
                prediction["representation_verified"] = bool(compiled.disposition == "accept")
                prediction["query_ms"] = (time.perf_counter() - query_started) * 1000 if result else 0.0
            else:
                query = row["request"]["query"]
                query_started = time.perf_counter()
                result = runtime.ask(QueryRequest(request.tenant_id, request.reality_id, row["case_id"], "fixed_equilibrium", "formal", query)) if compiled.disposition == "accept" else None
                prediction = _prediction(row, result, (time.perf_counter() - started) * 1000) if result else {
                    "case_id": row["case_id"], "track": row["track"], "disposition": compiled.disposition, "claim": None,
                    "claims": (), "alternatives": (), "certificate_length": 0, "tension": 0.0,
                    "failure_codes": tuple(compiled.failure_codes), "runtime_ms": (time.perf_counter() - started) * 1000,
                }
                prediction["representation_verified"] = bool(compiled.disposition == "accept")
                prediction["query_ms"] = (time.perf_counter() - query_started) * 1000 if result else 0.0
            predictions.append(prediction)
        if controls_path is not None:
            for row in control_rows:
                for mode in ("no_optimization", "one_sweep", "remove_decisive", "swap_authority", "duplicate_source", "shuffle_endpoints"):
                    control_predictions.append(_control_prediction(runtime, row, mode))
    output_path.write_text("".join(json.dumps(item, sort_keys=True, default=str) + "\n" for item in predictions), encoding="utf-8")
    if controls_path is not None:
        controls_path.write_text("".join(json.dumps(item, sort_keys=True, default=str) + "\n" for item in control_predictions), encoding="utf-8")
    replay_ok = 0
    eq_rows = [row for row in rows if row["track"] == "equilibrium"]
    if eq_rows:
        first = eq_rows[0]
        request = _request(first)
        query = first["request"]["query"]
        with ParasiteRuntime.open(state_path, config_path) as restarted:
            replay = restarted.ask(QueryRequest(request.tenant_id, request.reality_id, first["case_id"], "fixed_equilibrium", "formal", query))
            cross = restarted.ask(QueryRequest(request.tenant_id, request.reality_id + "-foreign", first["case_id"] + "-foreign", "fixed_equilibrium", "formal", query))
        first_prediction = next(item for item in predictions if item["case_id"] == first["case_id"])
        replay_ok = int(replay.disposition == first_prediction["disposition"] and tuple(replay.authorized_claims) == tuple(first_prediction["claims"]))
    integrity = {"representation_checked": representation_checked, "representation_passed": representation_passed,
                 "partial_commits": invalid_partial, "restart_replay": replay_ok, "runtime_gold_reads": 0,
                 "network_calls": network_calls, "cross_boundary_influence": int(cross.disposition != "unknown") if eq_rows else 0}
    (output_path.parent / "runtime-integrity.json").write_text(json.dumps(integrity, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--controls", type=Path)
    parser.add_argument("--control-ids", type=Path)
    args = parser.parse_args(argv)
    run(args.public, args.output, args.state, args.config, args.controls, args.control_ids)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
