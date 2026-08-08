from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from parasite.contracts import IngestRequest, QueryRequest
from parasite.optimizer.equilibrium import solve_equilibrium
from parasite.runtime import ParasiteRuntime

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "Parasite/config/runtime-v1.json"


def request(kind: str, payload: dict, *, tenant: str = "tenant-a", reality: str = "reality-a", source: str = "source-a", session: str | None = None) -> IngestRequest:
    text = payload["source_text"]
    return IngestRequest(tenant, reality, source, hashlib.sha256(text.encode()).hexdigest(), kind, payload, session_id=session)


def chain_payload(depth: int = 20, *, opposition: float | None = 0.4) -> dict:
    atoms = [{"id": f"a{i}", "expression": f"state-{i}", "sort": "custom"} for i in range(depth + 1)]
    factors = [
        {"id": f"b{i}", "inputs": [f"a{i}"], "outcome": f"a{i + 1}", "source_key": f"independent-{i}"}
        for i in range(depth)
    ]
    if opposition is not None:
        factors.append({
            "id": "opposition", "inputs": [f"a{depth - 1}"], "outcome": f"a{depth}", "polarity": -1,
            "authority": opposition, "source_key": "opposing-source",
        })
    return {"source_text": f"fixed custom chain {depth}", "atoms": atoms, "factors": factors}


def test_structured_topology_round_trip_and_restart(tmp_path):
    payload = {
        "source_text": "p implies q",
        "nodes": [
            {"id": "p", "kind": "claim", "attributes": {"label": "p"}},
            {"id": "q", "kind": "claim", "attributes": {"label": "q"}},
        ],
        "relations": [{
            "id": "rule", "relation_type": "implies",
            "arguments": [{"role": "premise", "node_id": "p"}, {"role": "conclusion", "node_id": "q"}],
        }],
    }
    with ParasiteRuntime.open(tmp_path, CONFIG) as runtime:
        compiled = runtime.ingest(request("topology_document", payload))
        assert compiled.disposition == "accept"
        answer = runtime.ask(QueryRequest("tenant-a", "reality-a", "q1", "exact", "topology", {"target_atom_id": "q"}))
        assert answer.disposition == "candidate"
        assert answer.authorized_claims == ("q",)
        first = runtime.verify("tenant-a", "reality-a")
    with ParasiteRuntime.open(tmp_path, CONFIG) as restarted:
        assert restarted.verify("tenant-a", "reality-a") == first
        assert restarted.inspect("tenant-a", "reality-a")["nodes"] == 2


def test_depth_twenty_equilibrium_duplicate_sources_and_isolation(tmp_path):
    with ParasiteRuntime.open(tmp_path, CONFIG) as runtime:
        compiled = runtime.ingest(request("mathematical_reality", chain_payload(), reality="custom-alpha"))
        assert compiled.disposition == "accept"
        result = runtime.ask(QueryRequest(
            "tenant-a", "custom-alpha", "q20", "fixed_equilibrium", "formal",
            {"assumptions": ["state-0"], "query_expression": "state-20", "query_sort": "custom"}, requested_style="detailed",
        ))
        assert result.disposition == "candidate"
        assert result.authorized_claims == ("state-20",)
        assert len(result.proof_or_equilibrium_certificate) == 20
        assert result.tension == pytest.approx(0.4)
        assert runtime.ask(QueryRequest(
            "tenant-a", "other-reality", "wrong", "fixed_equilibrium", "formal",
            {"assumptions": ["state-0"], "query_expression": "state-20", "query_sort": "custom"},
        )).disposition == "unknown"


def test_one_sweep_cannot_cross_twenty_and_cycles_abstain(tmp_path):
    with ParasiteRuntime.open(tmp_path, CONFIG) as runtime:
        runtime.ingest(request("mathematical_reality", chain_payload(opposition=None), reality="chain"))
        loaded = runtime.field.load("tenant-a", "chain")
        assert loaded is not None
        shallow = solve_equilibrium(
            loaded.atoms, loaded.factors, assumption_atom_ids=(next(atom.atom_id for atom in loaded.atoms if atom.expression == "state-0"),),
            query_expression="state-20", query_sort="custom", maximum_sweeps=1,
        )
        states = {item.atom_id: item.positive for item in shallow.states}
        assert states[next(atom.atom_id for atom in loaded.atoms if atom.expression == "state-1")] == 1.0
        assert states[next(atom.atom_id for atom in loaded.atoms if atom.expression == "state-2")] == 0.0
        assert shallow.disposition == "incomplete_equilibrium"

        cycle = {
            "source_text": "cyclic custom field",
            "atoms": [{"id": "x", "expression": "x", "sort": "custom"}, {"id": "y", "expression": "y", "sort": "custom"}],
            "factors": [
                {"id": "xy", "inputs": ["x"], "outcome": "y"},
                {"id": "yx", "inputs": ["y"], "outcome": "x"},
            ],
        }
        runtime.ingest(request("mathematical_reality", cycle, reality="cycle", source="cycle-source"))
        answer = runtime.ask(QueryRequest("tenant-a", "cycle", "cycle-q", "fixed_equilibrium", "formal", {"assumptions": ["x"], "query_expression": "y", "query_sort": "custom"}))
        assert answer.disposition == "verification_failed"
        assert "CYCLE_UNSUPPORTED" in answer.failure_codes


def test_invalid_compilation_and_tenant_boundary(tmp_path):
    payload = chain_payload(2, opposition=None)
    bad = IngestRequest("tenant-a", "r", "s", "0" * 64, "mathematical_reality", payload)
    with ParasiteRuntime.open(tmp_path, CONFIG) as runtime:
        assert runtime.ingest(bad).disposition == "quarantine"
        assert runtime.inspect("tenant-a", "r")["generation_id"] is None
        assert runtime.ingest(request("mathematical_reality", payload, tenant="tenant-a", reality="r")).disposition == "accept"
        assert runtime.inspect("tenant-b", "r")["generation_id"] is None


def test_session_clear_and_assistant_non_evidence(tmp_path):
    with ParasiteRuntime.open(tmp_path, CONFIG) as runtime:
        # Store an assistant response through an ordinary memory query.
        empty = runtime.ask(QueryRequest("t", "conversation", "q", "conversation_memory", "context", {}, session_id="s"))
        assert empty.disposition == "candidate"
        rows = runtime.field.session_rows("t", "conversation", "s")
        assert len(rows) == 1
        assert rows[0]["authority"] == 0.25
        assert rows[0]["non_evidence"] is True
        assert runtime.clear_session("t", "s") == 1
        assert runtime.field.session_rows("t", "conversation", "s") == ()


def test_decoder_rejects_unauthorized_renderer_claim():
    from parasite.decoder import decode

    result = decode(
        disposition="candidate", claims=("authorized",), verified=True,
        renderer=lambda _bundle: {"claims": ("invented",), "text": "Invented."},
    )
    assert "authorized" in result.response_text
    assert "Invented" not in result.response_text


def test_source_normalization_contradictions_and_conjunction(tmp_path):
    payload = {
        "source_text": "weighted contradiction and conjunction",
        "atoms": [
            {"id": "a", "expression": "a", "sort": "logic"},
            {"id": "b", "expression": "b", "sort": "logic"},
            {"id": "c", "expression": "c", "sort": "logic"},
        ],
        "factors": [
            {"id": "p1", "inputs": ["a"], "outcome": "c", "authority": 0.6, "source_key": "same-positive"},
            {"id": "p2", "inputs": ["a"], "outcome": "c", "authority": 0.6, "source_key": "same-positive"},
            {"id": "n1", "inputs": ["a"], "outcome": "c", "polarity": -1, "authority": 0.9, "source_key": "negative-1"},
            {"id": "n2", "inputs": ["a"], "outcome": "c", "polarity": -1, "authority": 0.9, "source_key": "negative-2"},
            {"id": "and", "inputs": ["a", "b"], "outcome": "c", "source_key": "conjunction"},
        ],
    }
    with ParasiteRuntime.open(tmp_path, CONFIG) as runtime:
        assert runtime.ingest(request("mathematical_reality", payload, reality="weighted")).disposition == "accept"
        negative = runtime.ask(QueryRequest("tenant-a", "weighted", "weighted-q", "fixed_equilibrium", "formal", {"assumptions": ["a"], "query_expression": "c", "query_sort": "logic"}))
        assert negative.authorized_claims == ("not c",)
        loaded = runtime.field.load("tenant-a", "weighted")
        assert loaded is not None
        atom_a = next(atom.atom_id for atom in loaded.atoms if atom.expression == "a")
        atom_c = next(atom.atom_id for atom in loaded.atoms if atom.expression == "c")
        state = solve_equilibrium(loaded.atoms, loaded.factors, assumption_atom_ids=(atom_a,), query_expression="c", query_sort="logic")
        c_state = next(item for item in state.states if item.atom_id == atom_c)
        assert c_state.positive == pytest.approx(0.6)  # duplicate positive source is not 0.84
        assert c_state.negative == pytest.approx(0.99)

        conjunction_only = replace_factor_subset(loaded.factors, "and")
        missing = solve_equilibrium(loaded.atoms, conjunction_only, assumption_atom_ids=(atom_a,), query_expression="c", query_sort="logic")
        assert missing.disposition == "unknown"


def replace_factor_subset(factors, body_public_suffix: str):
    # Public IDs are hashed, so select the only factor with two inputs.
    if body_public_suffix == "and":
        return tuple(item for item in factors if len(item.input_atom_ids) == 2)
    raise AssertionError(body_public_suffix)


def test_interrupted_commit_preserves_previous_generation(tmp_path, monkeypatch):
    with ParasiteRuntime.open(tmp_path, CONFIG) as runtime:
        first = runtime.ingest(request("mathematical_reality", chain_payload(2, opposition=None), reality="atomic"))
        assert first.disposition == "accept"
        previous = runtime.inspect("tenant-a", "atomic")["generation_id"]
        payload = {
            "source_text": "second atomic generation",
            "atoms": [{"id": "z0", "expression": "z0", "sort": "custom"}, {"id": "z1", "expression": "z1", "sort": "custom"}],
            "factors": [{"id": "z", "inputs": ["z0"], "outcome": "z1"}],
        }
        import parasite.field.store as store_module

        real_replace = store_module.os.replace

        def interrupted(source, destination):
            source_path, destination_path = Path(source), Path(destination)
            if source_path.parent == runtime.field.staging_root and len(destination_path.name) == 64:
                raise OSError("simulated interruption")
            return real_replace(source, destination)

        monkeypatch.setattr(store_module.os, "replace", interrupted)
        failed = runtime.ingest(request("mathematical_reality", payload, reality="atomic", source="second"))
        assert failed.disposition == "quarantine"
        assert runtime.inspect("tenant-a", "atomic")["generation_id"] == previous


def test_base_delete_creates_new_verified_generation(tmp_path):
    payload = chain_payload(2, opposition=None)
    with ParasiteRuntime.open(tmp_path, CONFIG) as runtime:
        created = runtime.ingest(request("mathematical_reality", payload, reality="delete-base"))
        target = dict(created.evidence)["object_ids"][-1]
        previous = runtime.inspect("tenant-a", "delete-base")["generation_id"]
        assert runtime.delete("tenant-a", "delete-base", target) is True
        current = runtime.inspect("tenant-a", "delete-base")
        assert current["generation_id"] != previous
        assert current["nodes"] == 2
        assert runtime.verify("tenant-a", "delete-base")["verified"] is True
