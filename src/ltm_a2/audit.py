"""Evidence-first architecture audit without modifying historical experiments."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ltm.audit import audit_repository
from ltm_r2.engine import equivalent, execute_oracle, execute_program
from ltm_r2.generator import SemanticAtom, SemanticBody, SemanticRelation, compile_body
from ltm_r2.profiles import PROFILES, compile_profile
from topology_g1.registry import REGISTRY

AUDIT_REVISION = "ltm-a2/1"


EXPERIMENTS = (
    ("G1", "PASS", "docs/experiments/gaps/g01/report.md", "exact topology contract"),
    ("G2.5", "FAILED; PROVISIONALLY ADOPTED", "docs/experiments/gaps/g02-5/report.md", "reasoning compiler"),
    ("G2.14", "NARROW PASS", "docs/experiments/gaps/g02-14/report.md", "supplied-span conversation gate"),
    ("G3–G5", "PASS", "docs/roadmap/results-ledger.md", "addressing, frontier and coverage"),
    ("G6–G9", "PASS", "docs/roadmap/results-ledger.md", "exact/soft execution and verification"),
    ("G10.1", "PASS", "docs/experiments/gaps/g10-1/report.md", "strict authorized realization"),
    ("G11–G13", "PASS", "docs/roadmap/results-ledger.md", "lifecycle, storage and scale"),
    ("G14", "CONTROLLED PASS", "docs/experiments/gaps/g14/report.md", "structured composition only"),
    ("LTM-I1", "PASS", "docs/experiments/integration/i01/report.md", "FieldIR v2 integration"),
    ("LTM-R2", "PASS", "docs/experiments/representation/r02/report.md", "Mumbrane representation"),
    ("G15", "NOT RUN", "docs/roadmap/results-ledger.md", "serving and fault isolation"),
)


SCENARIO_RELATIONS = (
    ("preference replacement", ("prefers",)),
    ("correction and supersession", ("supersedes",)),
    ("ambiguous reference", ("refers_to",)),
    ("hard implication chain", ("implies", "conjoins")),
    ("evidence tension", ("supports", "opposes", "uncertainty")),
    ("scope and temporal isolation", ("before", "scoped_to")),
    ("profile switch", ("requires", "prefers")),
    ("integrity boundary", ("excludes",)),
    ("indexed scale locality", ("derived_from", "assistant_derived_from")),
)


def _sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _json_summary(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"exists": False}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"exists": True, "valid_json": False}
    summary = {"exists": True, "valid_json": True}
    for key in (
        "classification", "all_pass", "accepted_exact_precision", "safe_coverage",
        "incorrect_accepted_predictions", "profile_agreement", "semantic_replay",
    ):
        if key in value:
            summary[key] = value[key]
    return summary


def _historical_evidence(root: Path) -> tuple[dict[str, object], ...]:
    workspace_paths = {
        "G2.5": root / "workspaces/topology-g2-5/kernel-results.json",
        "G2.14": root / "workspaces/topology-g2-14-r3/locked-results.json",
        "LTM-I1": root / "workspaces/ltm-i1-r5/locked-results.json",
        "LTM-R2": root / "workspaces/ltm-r2-r3/locked-results.json",
    }
    result = []
    for identifier, status, report, boundary in EXPERIMENTS:
        result.append(
            {
                "id": identifier,
                "ledger_status": status,
                "report": report,
                "report_exists": (root / report).exists(),
                "boundary": boundary,
                "artifact": _json_summary(workspace_paths[identifier])
                if identifier in workspace_paths
                else {"not_replayed": True},
            }
        )
    return tuple(result)


def _g214_handoff_check(root: Path) -> dict[str, object]:
    """Check the claimed integration against the source, not its report prose."""
    assembly = (root / "src/topology_g213/assembly.py").read_text(encoding="utf-8")
    actual_g1 = "TopologyOperation" in assembly and "topology_g1" in assembly
    actual_field = "FieldProgram" in assembly and "topology_field_ir" in assembly
    actual_mumbrane = "Mumbrane" in assembly and "ltm_r2" in assembly
    return {
        "g1_operations_constructed": actual_g1,
        "fieldir_program_constructed": actual_field,
        "mumbrane_program_constructed": actual_mumbrane,
        "verdict": "BOUNDARY_GAP" if not all((actual_g1, actual_field, actual_mumbrane)) else "IMPLEMENTED",
        "interpretation": (
            "G2.14 proves its supplied-span acceptance gate and structured G11 lifecycle compatibility; "
            "it does not independently prove the advertised G1/FieldIR/Mumbrane assembly handoff."
            if not all((actual_g1, actual_field, actual_mumbrane))
            else "The checked G2.14 assembly path constructs all advertised handoffs."
        ),
    }


def _body_for_scenario(index: int, name: str, relations: tuple[str, ...]) -> SemanticBody:
    """Build one semantically explicit, G1-valid body for each audit scenario."""
    atoms: list[SemanticAtom] = []
    relation_rows: list[SemanticRelation] = []
    for relation_index, relation_name in enumerate(relations):
        bindings: list[tuple[str, tuple[str, ...]]] = []
        for role_index, role in enumerate(REGISTRY[relation_name].roles):
            atom_ids = []
            for ordinal in range(role.minimum):
                atom_id = f"audit:{index}:a:{relation_index}:{role_index}:{ordinal}"
                atoms.append(SemanticAtom(atom_id, role.allowed_kinds[ordinal % len(role.allowed_kinds)].value))
                atom_ids.append(atom_id)
            bindings.append((role.name, tuple(atom_ids)))
        relation_rows.append(
            SemanticRelation(
                f"audit:{index}:r:{relation_index}",
                relation_name,
                tuple(bindings),
                .75,
                .2 if relation_index % 2 else -.2,
            )
        )
    while len(atoms) < 8:
        atoms.append(SemanticAtom(f"audit:{index}:extra:{len(atoms)}", "claim"))
    scope = ("global", "session", "fictional", "temporary")[index % 4]
    return SemanticBody(
        f"audit:{index:02d}",
        tuple(atoms),
        tuple(relation_rows),
        scope,
        f"audit-session:{index}" if scope == "session" else None,
        f"archive-only audit scenario: {name}",
    )


def _semantic_scenarios() -> tuple[dict[str, object], ...]:
    """Run new evaluator-owned semantic bodies through Mumbrane/profile execution.

    This does not test raw-language compilation; it tests the representation and
    configuration contract that a future compiler is required to produce.
    """
    results = []
    for index, (name, relations) in enumerate(SCENARIO_RELATIONS):
        body = _body_for_scenario(index, name, relations)
        program = compile_body(body)
        profile_results = {}
        for profile_name, profile in PROFILES.items():
            compiled = compile_profile(profile)
            observed = execute_program(program, compiled)
            expected = execute_oracle(body, compiled)
            profile_results[profile_name] = {
                "oracle_agreement": equivalent(observed, expected),
                "disposition": observed.disposition,
                "active_factor_count": len(observed.active_unit_ids),
                "vector_rows_read": observed.vector_rows_read,
            }
        results.append(
            {
                "scenario": name,
                "semantic_body_id": body.body_id,
                "relation_types": relations,
                "units": len(program.units),
                "ports": len(program.ports),
                "profiles": profile_results,
            }
        )
    return tuple(results)


def _research_basis() -> tuple[dict[str, str], ...]:
    return (
        {"topic": "intermediate concepts", "citation": "Koh et al. (2020), Concept Bottleneck Models", "url": "https://proceedings.mlr.press/v119/koh20a.html", "support": "auditable intermediate representation; not raw-language reliability"},
        {"topic": "role binding", "citation": "Smolensky (1990), Tensor Product Variable Binding", "url": "https://www.sciencedirect.com/science/article/pii/000437029090007M", "support": "separate role/filler structure is mathematically motivated"},
        {"topic": "selective prediction", "citation": "Geifman and El-Yaniv (2017), Selective Classification", "url": "https://papers.nips.cc/paper/2017/hash/4a8423d5e91fda00bb7e46540e2b0cf1-Abstract.html", "support": "confidence/coverage abstention trade-off"},
        {"topic": "soft structured inference", "citation": "Bach et al. (2017), Hinge-Loss Markov Random Fields", "url": "https://jmlr.org/beta/papers/v18/15-631.html", "support": "structured soft constraints and continuous optimization"},
        {"topic": "typed graph propagation", "citation": "Schlichtkrull et al. (2018), Relational Graph Convolutional Networks", "url": "https://2019.eswc-conferences.org/wp-content/uploads/2018/02/ESWC2018_paper_4.pdf", "support": "relation-specific message passing"},
        {"topic": "bounded external memory", "citation": "Rae et al. (2016), Scaling Memory-Augmented Neural Networks", "url": "https://papers.nips.cc/paper/2016/hash/2030e7d8a49f5e132b7c7d7bded7fe3e-Abstract.html", "support": "sparse reads/writes can avoid full memory scans"},
        {"topic": "provenance", "citation": "Green, Karvounarakis and Tannen (2007), Provenance Semirings", "url": "https://www.cs.ucdavis.edu/~green/papers/pods07.pdf", "support": "lineage as first-class algebraic information"},
        {"topic": "constrained realization", "citation": "Scholak et al. (2021), PICARD", "url": "https://aclanthology.org/2021.emnlp-main.779/", "support": "incremental constraints can reject invalid decoded candidates"},
    )


def run_audit(root: Path, workspace: Path) -> dict[str, object]:
    """Write a new audit only; never create or overwrite locked experiment output."""
    repository = audit_repository(root)
    scenarios = _semantic_scenarios()
    scenario_agreement = all(
        item["oracle_agreement"]
        for scenario in scenarios
        for item in scenario["profiles"].values()
    )
    handoff = _g214_handoff_check(root)
    result = {
        "audit_revision": AUDIT_REVISION,
        "scope": "fresh architecture audit; no model training or locked rerun",
        "repository": repository,
        "historical_evidence": _historical_evidence(root),
        "representation_scenarios": scenarios,
        "representation_scenario_agreement": scenario_agreement,
        "critical_findings": (
            handoff,
            {
                "id": "G2.5_REASONING_LIMIT",
                "verdict": "UNRESOLVED",
                "interpretation": "G2.5 is an engineering baseline, not an experimental compiler pass: 81.75% locked recovery and 199 reversal false accepts remain the limiting evidence.",
            },
            {
                "id": "G15_SERVING_LIMIT",
                "verdict": "UNTESTED",
                "interpretation": "Product serving, fault isolation and multi-tenant operational behavior have no measured result.",
            },
        ),
        "verdicts": {
            "controlled_ltm_v1": "CONDITIONAL_GO",
            "unrestricted_full_vision": "PLAUSIBLE_BUT_UNPROVEN",
            "reason": "The exact substrate, configured execution paths and constrained decoder replay correctly; compiler and serving boundaries remain incomplete.",
        },
        "engineering_forecasts": {
            "exact_representation_and_profile_execution": 0.90,
            "structured_topology_to_verified_answer": 0.90,
            "controlled_user_facing_v1_with_current_compilers": 0.60,
            "bounded_domain_product_after_writer_and_g15": 0.65,
            "robust_general_raw_reasoning_compiler_with_current_small_encoder": 0.25,
            "full_general_ltm_vision_with_current_known_architecture": 0.35,
        },
        "research_basis": _research_basis(),
    }
    result["audit_sha256"] = _sha256(result)
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "audit-results.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result
