from __future__ import annotations

import re
import time
from dataclasses import replace

from topology_g3.indexes import Indexes
from topology_g3.resolver import resolve
from topology_g3.schemas import PromptMention, PromptSignature, TopologyAddress
from topology_g4.indexes import FactorIndexes
from topology_g4.schemas import TopologyFactor, TraversalRequest
from topology_g4.traverse import build_frontier
from topology_g5.certificate import issue_certificate
from topology_g5.latent import force_for
from topology_g5.regions import RegionStore
from topology_g5.schemas import FactorInfluence
from topology_g5.summaries import SummaryCatalog
from topology_g5.summary_index import SummaryIndexes
from topology_g6.engine import execute as execute_g6
from topology_g6.schemas import ReasoningProblem, Rule
from topology_g7.optimize import reconcile
from topology_g7.schemas import ReconciliationProblem, SoftFactor, SoftVariable
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
from topology_g9.verifier import verify

from .schemas import BenchmarkQuery, ComponentTrace, MethodResult, MethodSpec


def _entity(query: BenchmarkQuery) -> str:
    match = re.search(r"(opaque-[^? ]+)", query.prompt)
    if not match:
        raise ValueError("query lacks addressable entity")
    return match.group(1)


def _target(query: BenchmarkQuery) -> str:
    return f"target:{query.query_id}"


def _program(query: BenchmarkQuery, *, include_session: bool = True, include_remote: bool = True) -> ReasoningProblem:
    target = _target(query)
    facts = list(query.facts)
    if query.session_required and not include_session:
        facts = []
    rules: list[Rule] = []
    for rule_id, premises, conclusion in query.rules:
        if query.coverage_required and rule_id.endswith(str(query.proof_depth - 1)) and not include_remote:
            continue
        rules.append(Rule(rule_id, "implies", premises, conclusion))
    return ReasoningProblem(query.query_id, query.family, tuple(facts), tuple(rules), target, depth=query.proof_depth)


class RealPipeline:
    """Actual G3/G4/G5/G6/G7/G9 calls over a compact shared typed topology."""

    def __init__(self, queries: tuple[BenchmarkQuery, ...]):
        self.queries = queries
        addresses: list[TopologyAddress] = []
        factors: list[TopologyFactor] = []
        factor_regions: dict[str, str] = {}
        for query in queries:
            entity = _entity(query); entity_id = f"address:entity:{query.conversation_id}"; predicate_id = f"address:predicate:{query.conversation_id}"
            addresses.extend((
                TopologyAddress(entity_id, query.conversation_id, "entity", entity, (entity.upper(),), None, None, "global", None, None, query.conversation_id if query.session_required else None, "entity", (f"src:{query.conversation_id}",)),
                TopologyAddress(predicate_id, f"predicate:{query.conversation_id}", "predicate", "state", (), "state", None, "global", None, None, None, "predicate", (f"src:{query.conversation_id}",)),
            ))
            program = _program(query)
            for fact_index, fact in enumerate(program.facts):
                factor_id = f"factor:{query.query_id}:fact:{fact_index}"; remote = False
                factor = TopologyFactor(factor_id, "session_fact" if query.session_required else "fact", (), (fact,), "global", episode_id=query.conversation_id if query.session_required else None, session_factor=query.session_required, provenance_ids=("src:user",))
                factors.append(factor); factor_regions[factor_id] = f"region:{query.query_id}:local"
            for rule in program.rules:
                factor_id = f"factor:{query.query_id}:{rule.rule_id}"; remote = query.coverage_required and rule.rule_id.endswith(str(query.proof_depth - 1))
                factor = TopologyFactor(factor_id, "implies", rule.premises, (rule.conclusion or "",), "global", bridge_region_id="remote" if remote else None, provenance_ids=("src:rule",))
                factors.append(factor); factor_regions[factor_id] = f"region:{query.query_id}:{'remote' if remote else 'local'}"
        self.addresses = tuple(addresses); self.factors = tuple(factors); self.factor_indexes = FactorIndexes(self.factors)
        self.addresses_index = Indexes(self.addresses)
        self.region_store = RegionStore(self.factors, factor_regions)
        # G4 initially sees only locally opened regions. G5 must explicitly widen
        # into any remote final-rule region instead of inheriting it by accident.
        self.initial_factor_indexes = FactorIndexes(tuple(
            factor for factor in self.factors if self.region_store.region_for(factor.factor_id).endswith(":local")
        ))
        influences = tuple(FactorInfluence(factor.factor_id, (_target(query),) if factor.factor_id.startswith(f"factor:{query.query_id}:") else (), force_for(factor.factor_id, .02), .02) for query in queries for factor in self.factors if factor.factor_id.startswith(f"factor:{query.query_id}:"))
        self.catalog = SummaryCatalog(self.region_store, influences, {})
        self.summary_indexes = SummaryIndexes(self.catalog)

    def _signature(self, query: BenchmarkQuery) -> PromptSignature:
        entity = _entity(query); start = query.prompt.index(entity)
        return PromptSignature(query.query_id, "question", (PromptMention(entity, entity, "entity", start, start + len(entity)),), ("state",), (), (), ("global",), None, None, "positive", "asserted", (query.conversation_id,) if query.session_required else (), "retain")

    def _program_from_factors(self, query: BenchmarkQuery, factor_ids: tuple[str, ...]) -> ReasoningProblem:
        facts: list[str] = []
        rules: list[Rule] = []
        for factor_id in factor_ids:
            factor = self.region_store.factors[factor_id]
            if factor.factor_type in {"fact", "negative_fact", "session_fact"}:
                facts.extend(factor.target_ids)
            elif factor.factor_type == "implies":
                rules.append(Rule(factor.factor_id.removeprefix(f"factor:{query.query_id}:"), "implies", factor.source_ids, factor.target_ids[0]))
        return ReasoningProblem(query.query_id, query.family, tuple(sorted(facts)), tuple(sorted(rules, key=lambda item: item.rule_id)), _target(query), depth=query.proof_depth)

    def _bundle(self, query: BenchmarkQuery, program: ReasoningProblem, hard, certificate) -> CandidateBundle:
        source_user = SourceRecord("src:user", "user", query.prompt, __import__("hashlib").sha256(query.prompt.encode()).hexdigest(), 1.0)
        source_rule = SourceRecord("src:rule", "document", "registered rule", __import__("hashlib").sha256(b"registered rule").hexdigest(), 1.0)
        address = AddressRecord(f"address:entity:{query.conversation_id}", "entity", "global", query.conversation_id, None, None)
        facts = tuple(FactRecord(f"fact:{number}", literal, address.address_id, ("src:user",), "global", None, None) for number, literal in enumerate(program.facts))
        rules = tuple(RuleRecord(rule.rule_id, rule.kind, rule.premises, rule.conclusion, "global", ("src:rule",)) for rule in program.rules)
        proof = tuple(ProofRecord(item.conclusion, item.rule_id, item.premises, item.depth) for item in hard.proofs)
        soft = SoftRecord(("confidence",), (SoftFactorRecord("evidence", "confidence", .8, 1.0, None, "src:user"),), (), (("confidence", .8),), None, (), 0.0, (("evidence", 0.0),))
        manifest = tuple(sorted(self.region_store.regions)); opened = tuple(sorted(certificate.opened_region_ids)); summarized = tuple(sorted(set(manifest) - set(opened)))
        coverage = CoverageRecord(manifest, opened, summarized, (), (), (), ("hard-index",), ("exception-index",), 0.0, .02, "certified")
        return CandidateBundle(query.query_id, "topology-v1", "field-v1", address.address_id, program.target, "global", query.conversation_id, 0, (source_user, source_rule), (address,), facts, rules, (), (), (), hard.conclusion, proof, hard.conflicts, coverage, soft, ("src:rule", "src:user"), 1.0, False)

    def run(self, query: BenchmarkQuery, method: MethodSpec) -> MethodResult:
        started = time.perf_counter_ns(); signature = self._signature(query); addressing = resolve(signature, self.addresses_index)
        target = _target(query); request = TraversalRequest(query.query_id, addressing.resolved_addresses[:1], (f"address:predicate:{query.conversation_id}",), target, "global", None, query.conversation_id if query.session_required and method.method_id != "no_session_overlay" else None, "positive")
        mode = "no_session" if method.method_id == "no_session_overlay" else "full"
        frontier = build_frontier(request, self.initial_factor_indexes, mode=mode)
        opened_regions = {self.region_store.region_for(fid) for fid in frontier.exact_factor_ids}
        certificate = issue_certificate(request, self.region_store, self.catalog, self.summary_indexes, opened_regions, (), "unknown")
        if certificate.disposition == "widen_required" and method.method_id != "no_coverage":
            opened_regions.update(certificate.next_region_ids)
            certificate = issue_certificate(request, self.region_store, self.catalog, self.summary_indexes, opened_regions, (), "unknown")
            # Re-enter the real G4 traversal after G5 has authorized exact region
            # opening, so prerequisite factors are recovered through typed edges.
            widened_indexes = FactorIndexes(tuple(
                factor for factor in self.factors
                if self.region_store.region_for(factor.factor_id) in opened_regions
                or self.region_store.region_for(factor.factor_id).endswith(":local")
            ))
            frontier = build_frontier(request, widened_indexes, mode=mode)
            opened_regions.update(self.region_store.region_for(fid) for fid in frontier.exact_factor_ids)
        selected_ids = set(frontier.exact_factor_ids)
        for region_id in opened_regions:
            selected_ids.update(item.factor_id for item in self.region_store.open_region(region_id))
        program = self._program_from_factors(query, tuple(sorted(selected_ids)))
        if method.method_id == "no_exact_propagation":
            program = ReasoningProblem(program.problem_id, program.family, program.facts, (), program.target, depth=program.depth)
        hard = execute_g6(program)
        if method.method_id != "no_soft_optimization":
            soft = ReconciliationProblem(query.query_id, query.family, program, (SoftVariable("confidence", "confidence", 0, 1, .5),), (SoftFactor("evidence", "evidence", ("confidence",), (.8,), 1, 1, 1, "src:user"),), (), ())
            reconcile(soft, {"maximum_steps": 12, "learning_rate": .05, "backtracking_retries": 4, "convergence_tolerance": 1e-7, "accepted_energy_tolerance": 1e-10, "maximum_evaluations": 80, "decision_margin": .05, "abstention_threshold": .75})
        verified = verify(self._bundle(query, program, hard, certificate)) if method.method_id != "no_verifier" else None
        conclusion = hard.conclusion
        # Retrieval controls receive a bounded evidence prefix, never evaluator labels.
        if method.method_id in {"hybrid_rag", "summary_qwen"}:
            retained = tuple(rule for rule in program.rules if rule.rule_id.endswith(":0"))
            hard = execute_g6(ReasoningProblem(program.problem_id, program.family, program.facts, retained, program.target, depth=program.depth))
            conclusion = hard.conclusion
        trace = ComponentTrace(query.query_id, method.method_id, addressing.resolved_addresses, tuple(sorted(selected_ids)), certificate.disposition, hard.conclusion, verified.status if verified else "not_run", not query.session_required or request.episode_id is not None, frontier.budget_exhausted, (time.perf_counter_ns() - started) // 1000)
        return MethodResult(query.query_id, method.method_id, conclusion, "resolved" if conclusion != "unknown" else "unknown", hard.proofs and tuple(sorted({"src:user", "src:rule"})) or (), trace)

    def verifier_attack_rejected(self, query: BenchmarkQuery) -> bool:
        """Run G9 on a plausible bundle whose claimed conclusion was altered."""
        program = _program(query)
        hard = execute_g6(program)
        request = TraversalRequest(query.query_id, (), (), _target(query), "global", None, query.conversation_id if query.session_required else None, "positive")
        regions = set(self.region_store.regions)
        certificate = issue_certificate(request, self.region_store, self.catalog, self.summary_indexes, regions, (), hard.conclusion)
        alternate = "contradicted" if hard.conclusion != "contradicted" else "entailed"
        result = verify(replace(self._bundle(query, program, hard, certificate), claimed_conclusion=alternate))
        return result.status == "rejected" and result.failure_codes == ("HARD_STATE_MISMATCH",)
