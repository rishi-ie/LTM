from __future__ import annotations

from pathlib import Path

from ltm.adapters import from_g1
from ltm.codec import artifact_hash, semantic_hash, unpack_program
from ltm.execution import (
    ExecutionRequest,
    VectorStore,
    build_execution_view,
    execute_hard,
    g3_addresses,
    g4_factors,
    g5_coverage,
)
from topology_g7.optimize import reconcile
from topology_g7.oracle import solve as solve_oracle
from topology_g9.generator import build as g9_build
from topology_g9.verifier import verify as verify_g9
from topology_g10.generator import build as g10_build
from topology_g101.model import FlanCandidateScorer
from topology_g101.realize import realize

from .field import build_field
from .legacy import legacy_problem
from .schemas import IntegrationCase, IntegrationResult


def _prototypes(program) -> dict[str, tuple[float, ...]]:
    relation_names = (name for name, _code in program.config.relation_codes)
    return {name: tuple(1.0 / (256 ** 0.5) for _ in range(256)) for name in relation_names}


def run_case(case: IntegrationCase, root: Path, scorer: FlanCandidateScorer | None = None) -> IntegrationResult:
    failures: list[str] = []
    field_root = root / "fields" / case.case_id
    program, archive = build_field(case, field_root)
    original_semantic, original_artifact = semantic_hash(program), artifact_hash(program)
    try:
        loaded = unpack_program(field_root, program.config, archive)
    except (OSError, ValueError) as error:
        return IntegrationResult(case.case_id, False, False, False, False, False, False, False, False, False, False, 0, (type(error).__name__, str(error)))
    semantic_equal = semantic_hash(loaded) == original_semantic
    artifact_equal = artifact_hash(loaded) == original_artifact
    nodes, relations = __import__("ltm.adapters", fromlist=["to_g1"]).to_g1(loaded, archive)
    projection_equal = tuple(node.node_id for node in nodes) == tuple(node.node_id for node in case.nodes) and relations[0].relation_type == case.relation.relation_type
    legacy_program, _legacy_archive = from_g1(nodes, relations, loaded.config)
    address_equal = g3_addresses(loaded) == g3_addresses(legacy_program)
    frontier_equal = g4_factors(loaded) == g4_factors(legacy_program)
    coverage_equal = g5_coverage(loaded, case.case_id) == g5_coverage(legacy_program, case.case_id)
    request = ExecutionRequest(case.case_id, case.target_atom_id, case.nodes[0].scope_id, None, 10)
    vectors = VectorStore(loaded, field_root)
    view = build_execution_view(loaded, vectors, _prototypes(loaded), request, original_semantic)
    canonical_hard = execute_hard(view)
    legacy_hard = __import__("topology_g6.engine", fromlist=["execute"]).execute(legacy_problem(loaded, request))
    hard_equal = canonical_hard == legacy_hard
    settings = {"decision_margin": .05, "abstention_threshold": .8, "maximum_steps": 100, "learning_rate": .1, "backtracking_retries": 10, "accepted_energy_tolerance": 1e-12, "convergence_tolerance": 1e-8, "maximum_evaluations": 1000}
    optimized = reconcile(view.g7_problem, settings)
    oracle = solve_oracle(view.g7_problem, settings)
    soft_equal = (
        optimized.selected_branch == oracle["selected_branch"]
        and optimized.disposition == oracle["disposition"]
        and abs(optimized.final_energy - oracle["energy"]) <= 1e-10
    )
    g9_bundles, _ = g9_build(20261001, 1, {"topology_version": "topology-v1", "field_version": "field-v1"})
    g9_result = verify_g9(g9_bundles[0])
    g9_equal = g9_result.status == "verified"
    decoder_equal = True
    if scorer is not None:
        bundles, _ = g10_build(20261002, 1)
        ranked = realize(bundles[0], scorer)
        replayed = realize(bundles[0], scorer)
        decoder_equal = ranked.validator_accepted and ranked.selected.text == replayed.selected.text and ranked.selected.template_id == replayed.selected.template_id
    for name, value in (("semantic", semantic_equal), ("artifact", artifact_equal), ("projection", projection_equal), ("address", address_equal), ("frontier", frontier_equal), ("coverage", coverage_equal), ("hard", hard_equal), ("soft", soft_equal), ("g9", g9_equal), ("decoder", decoder_equal)):
        if not value: failures.append(f"{name.upper()}_MISMATCH")
    return IntegrationResult(case.case_id, semantic_equal, artifact_equal, projection_equal, address_equal, frontier_equal, coverage_equal, hard_equal, soft_equal, g9_equal, decoder_equal, vectors.rows_read, tuple(failures))
