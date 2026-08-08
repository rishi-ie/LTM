"""Canonical FieldIR projection into the registered G6/G7 execution lanes."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from ltm.codec import semantic_hash
from ltm.execution import ExecutionRequest, VectorStore, build_execution_view, execute_hard
from topology_g7.optimize import reconcile
from topology_g9.schemas import (
    AddressRecord,
    CandidateBundle,
    CoverageRecord,
    FactRecord,
    ProofRecord,
    RuleRecord,
    SoftFactorRecord,
    SoftRecord,
    SourceRecord,
)
from topology_g9.verifier import verify as g9_verify


@dataclass(frozen=True, slots=True)
class ExactExecutionResult:
    disposition: str
    authorized_claims: tuple[str, ...]
    proof_ids: tuple[str, ...]
    conflicts: tuple[str, ...]
    uncertainty: float
    verified: bool
    failure_codes: tuple[str, ...]


def execute_exact(loaded, *, query_id: str, target_atom_id: str, scope_key: str, session_id: str | None, valid_at: int | None) -> ExactExecutionResult:
    request = ExecutionRequest(query_id, target_atom_id, scope_key, session_id, valid_at)
    view = build_execution_view(
        loaded.fieldir, VectorStore(loaded.fieldir, loaded.root / "fieldir"), {}, request,
        semantic_hash(loaded.fieldir), coverage_disposition="certified", require_vectors=False,
    )
    hard = execute_hard(view)
    settings = {
        "maximum_steps": 64, "convergence_tolerance": 1e-8, "learning_rate": 0.1,
        "backtracking_retries": 12, "accepted_energy_tolerance": 1e-12,
        "maximum_evaluations": 4096, "decision_margin": 0.05, "abstention_threshold": 0.95,
    }
    soft = reconcile(view.g7_problem, settings)
    proof_ids = tuple(step.rule_id for step in hard.proofs if step.conclusion == target_atom_id)
    user_text, rule_text = "Parasite exact request", "Parasite registered field rules"
    address_id = f"address:{query_id}"
    sources = (
        SourceRecord("src:user", "user", user_text, hashlib.sha256(user_text.encode()).hexdigest(), 1.0),
        SourceRecord("src:rule", "document", rule_text, hashlib.sha256(rule_text.encode()).hexdigest(), 1.0),
    )
    address = AddressRecord(address_id, "field_atom", scope_key, session_id or "sessionless", None, None)
    facts = tuple(FactRecord(f"fact:{index}", literal, address_id, ("src:user",), scope_key, None, None) for index, literal in enumerate(view.g6_problem.facts))
    rules = tuple(RuleRecord(rule.rule_id, rule.kind, rule.premises, rule.conclusion, scope_key, ("src:rule",)) for rule in view.g6_problem.rules)
    proof = tuple(ProofRecord(step.conclusion, step.rule_id, step.premises, step.depth) for step in hard.proofs)
    coverage = CoverageRecord(("complete-partition",), ("complete-partition",), (), (), (), (), ("fieldir-hard",), ("fieldir-exception",), 0.0, 0.0, "certified")
    soft_record = SoftRecord(
        ("confidence",), (SoftFactorRecord("parasite-soft", "confidence", 0.8, 1.0, None, "src:user"),), (),
        (("confidence", 0.8),), None, (), 0.0, (("parasite-soft", 0.0),),
    )
    bundle = CandidateBundle(
        query_id, "topology-v1", "field-v1", address_id, target_atom_id, scope_key, session_id or "sessionless", valid_at or 0,
        sources, (address,), facts, rules, (), tuple(rule.rule_id for rule in rules), tuple(rule.rule_id for rule in rules),
        hard.conclusion, proof, hard.conflicts, coverage, soft_record, ("src:rule", "src:user"), 1.0, True,
    )
    verification = g9_verify(bundle)
    valid = verification.status.startswith("verified") and verification.authorized_conclusion == target_atom_id
    authorized = (target_atom_id,) if valid else ()
    disposition = "candidate" if authorized else "unknown" if verification.status == "unknown" else "verification_failed"
    uncertainty = float(soft.final_state.uncertainty)
    return ExactExecutionResult(disposition, authorized, proof_ids, hard.conflicts, uncertainty, valid, verification.failure_codes)
