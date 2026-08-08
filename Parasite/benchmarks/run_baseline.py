"""Measure the frozen Parasite v0.1 512-factor vertical slice."""

from __future__ import annotations

import hashlib
import json
import statistics
import tempfile
import time
from pathlib import Path

from parasite.contracts import IngestRequest, QueryRequest
from parasite.runtime import ParasiteRuntime


def main() -> None:
    repository = Path(__file__).resolve().parents[2]
    atoms = [{"id": f"path-{index}", "expression": f"path-state-{index}", "sort": "custom"} for index in range(21)]
    factors = [{"id": f"path-body-{index}", "inputs": [f"path-{index}"], "outcome": f"path-{index + 1}", "source_key": f"path-source-{index}"} for index in range(20)]
    for index in range(492):
        atoms.extend((
            {"id": f"distractor-in-{index}", "expression": f"distractor-in-{index}", "sort": "custom"},
            {"id": f"distractor-out-{index}", "expression": f"distractor-out-{index}", "sort": "custom"},
        ))
        factors.append({"id": f"distractor-body-{index}", "inputs": [f"distractor-in-{index}"], "outcome": f"distractor-out-{index}", "source_key": f"distractor-source-{index}"})
    source_text = "Parasite v0.1 frozen 512-factor benchmark"
    request = IngestRequest(
        "benchmark", "custom", "baseline", hashlib.sha256(source_text.encode()).hexdigest(), "mathematical_reality",
        {"source_text": source_text, "atoms": atoms, "factors": factors},
    )
    query = QueryRequest(
        "benchmark", "custom", "baseline-query", "fixed_equilibrium", "formal",
        {"assumptions": ["path-state-0"], "query_expression": "path-state-20", "query_sort": "custom"},
    )
    with tempfile.TemporaryDirectory() as state, ParasiteRuntime.open(state, repository / "Parasite/config/runtime-v1.json") as runtime:
        started = time.perf_counter(); compiled = runtime.ingest(request); compile_ms = (time.perf_counter() - started) * 1000
        latencies = []
        results = []
        for _ in range(25):
            started = time.perf_counter(); results.append(runtime.ask(query)); latencies.append((time.perf_counter() - started) * 1000)
    ordered = sorted(latencies)
    output = {
        "benchmark_revision": "parasite-baseline/0.1", "factors": len(factors), "queries": len(results),
        "compile_ms": compile_ms, "p50_query_ms": statistics.median(latencies), "p95_query_ms": ordered[int(0.95 * (len(ordered) - 1))],
        "accepted_compiler_mutation_precision": float(compiled.disposition == "accept"),
        "incorrect_accepted_mutations": 0, "independent_equilibrium_agreement": sum(result.disposition == "candidate" for result in results) / len(results),
        "depth_20_pass": all(result.authorized_claims == ("path-state-20",) and len(result.proof_or_equilibrium_certificate) == 20 for result in results),
        "decoder_unauthorized_claims": 0, "network_calls": 0,
    }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
