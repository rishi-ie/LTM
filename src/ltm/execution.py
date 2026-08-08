"""Adapters from canonical FieldIR v2 into the registered runtime contracts.

The historical G3--G10.1 packages remain independent.  This module owns the
small, explicit projection from the canonical numeric field into those
contracts and keeps exact G1 bindings separate from continuous soft state.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from topology_field_ir.codec import read_vector_sidecar
from topology_g3.schemas import TopologyAddress
from topology_g4.schemas import TopologyFactor as FrontierFactor
from topology_g5.schemas import CoverageCertificate
from topology_g6.engine import execute
from topology_g6.schemas import ReasoningProblem, Rule
from topology_g7.schemas import (
    DiscreteAlternative,
    ReconciliationProblem,
    SoftFactor,
    SoftVariable,
)
from topology_g9.schemas import CandidateBundle, VerificationResult
from topology_g101.schemas import RankedRealization

from .schema import FieldProgramV2, SourceArchive, SurfaceClaimRecord


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    request_id: str
    target_atom_id: str
    scope_key: str
    session_key: str | None
    valid_at: int | None
    requested_style: str = "brief"
    maximum_regions: int = 4


@dataclass(frozen=True, slots=True)
class FieldExecutionView:
    field_semantic_sha256: str
    selected_atom_ids: tuple[str, ...]
    selected_factor_ids: tuple[str, ...]
    coverage_disposition: str
    g6_problem: ReasoningProblem
    g7_problem: ReconciliationProblem


@dataclass(frozen=True, slots=True)
class VerifiedFieldEnvelope:
    field_manifest: object
    request: ExecutionRequest
    g9_bundle: CandidateBundle


@dataclass(frozen=True, slots=True)
class AuthorizedAnswerView:
    request_id: str
    status: str
    authorized_claim_ids: tuple[str, ...]
    proof_ids: tuple[str, ...]
    provenance_ids: tuple[str, ...]
    conflicts: tuple[str, ...]
    uncertainty: float
    style: str


@dataclass(frozen=True, slots=True)
class IntegrationTrace:
    field_semantic_sha256: str
    region_ids: tuple[str, ...]
    factor_ids: tuple[str, ...]
    vector_rows_read: int
    hard_conclusion: str
    verifier_status: str


@dataclass(frozen=True, slots=True)
class FieldExecutionResult:
    request_id: str
    field_semantic_sha256: str
    hard_result: object
    soft_result: object
    verification: VerificationResult
    decoder_result: RankedRealization | None
    trace: IntegrationTrace


def authorized_answer(request: ExecutionRequest, verification: VerificationResult, *, uncertainty: float, style: str) -> AuthorizedAnswerView:
    """Reduce a verified envelope to decoder-authorized metadata only."""
    return AuthorizedAnswerView(
        request.request_id,
        verification.status,
        (verification.authorized_conclusion,) if verification.authorized_conclusion else (),
        tuple(f"proof:{index}" for index, _ in enumerate(verification.verified_proof)),
        verification.verified_provenance_ids,
        verification.conflicts,
        uncertainty,
        style,
    )


class VectorStore:
    """Hash-checked read-only access to v2 vector sidecars."""

    def __init__(self, program: FieldProgramV2, root: Path):
        self.program = program
        self.root = root
        self._rows: dict[int, tuple[float, ...]] = {}
        self._reads = 0
        self._spaces = {space.space_id: space for space in program.config.vector_spaces}

    @property
    def rows_read(self) -> int:
        return self._reads

    def row(self, vector_index: int) -> tuple[float, ...]:
        if vector_index in self._rows:
            return self._rows[vector_index]
        if not 0 <= vector_index < len(self.program.vectors):
            raise ValueError("VECTOR_REFERENCE_OUT_OF_RANGE")
        reference = self.program.vectors[vector_index]
        space = self._spaces[reference.space_id]
        path = self.root / f"{reference.space_id}.ltmf"
        vector = read_vector_sidecar(path, reference.sidecar_sha256, reference.row_index, reference.row_sha256)
        if len(vector) != space.dimension or not all(math.isfinite(value) for value in vector):
            raise ValueError("VECTOR_DIMENSION_OR_FINITE_FAILURE")
        if space.normalized:
            norm = math.sqrt(sum(value * value for value in vector))
            if not math.isclose(norm, 1.0, rel_tol=1e-5, abs_tol=1e-5):
                raise ValueError("VECTOR_NORMALIZATION_FAILURE")
        self._rows[vector_index] = tuple(float(value) for value in vector)
        self._reads += 1
        return self._rows[vector_index]


def _roles(program: FieldProgramV2, factor_index: int) -> dict[str, tuple[str, ...]]:
    role_by_code = {code: name for name, code in program.config.role_codes}
    factor = program.factors[factor_index]
    grouped: dict[str, list[str]] = {}
    for binding in program.bindings[factor.binding_start : factor.binding_start + factor.binding_count]:
        grouped.setdefault(role_by_code[binding.role_code], []).append(program.atoms[binding.atom_index].atom_id)
    return {role: tuple(values) for role, values in grouped.items()}


def _rule_rows(program: FieldProgramV2) -> tuple[tuple[str, Rule], ...]:
    relation_by_code = {code: name for name, code in program.config.relation_codes}
    rows: list[tuple[str, Rule]] = []
    for index, factor in enumerate(program.factors):
        relation = relation_by_code[factor.operator_code]
        roles = _roles(program, index)
        scope = program.contexts[factor.context_index].scope_key
        factor_id, scope_key = factor.factor_id, scope
        def add(suffix: str, kind: str, premises: tuple[str, ...], conclusion: str | None = None, *, _factor_id=factor_id, _scope_key=scope_key) -> None:
            rows.append((f"{_factor_id}:{suffix}", Rule(f"{_factor_id}:{suffix}", kind, premises, conclusion, _scope_key)))
        if relation in {"implies", "fictional_rule", "conjoins"}:
            premises = roles.get("premise", ())
            add("derive", "fictional_rule" if relation == "fictional_rule" else "conjoins" if relation == "conjoins" else "implies", premises, roles.get("conclusion", (None,))[0])
        elif relation == "derived_from":
            add("derive", "derived_from", roles.get("source", ()), roles.get("derived", (None,))[0])
        elif relation == "assistant_derived_from":
            add("derive", "assistant_derived_from", roles.get("evidence", ()), roles.get("response", (None,))[0])
        elif relation == "requires":
            add("require", "requires", roles.get("dependent", ()) + roles.get("prerequisite", ()))
        elif relation == "excludes":
            add("exclude", "excludes", roles.get("left", ()) + roles.get("right", ()))
        elif relation == "supersedes":
            add("supersede", "supersedes", roles.get("older", ()) + roles.get("newer", ()))
        elif relation == "scoped_to":
            add("scope", "scoped_to", roles.get("subject", ()) + roles.get("scope", ()))
        elif relation == "refers_to":
            add("reference", "refers_to", roles.get("mention", ()) + roles.get("entity", ()))
        elif relation == "equals":
            left, right = roles.get("left", (None,))[0], roles.get("right", (None,))[0]
            if left is not None and right is not None:
                add("left-right", "equals", (left,), right)
                add("right-left", "equals", (right,), left)
        elif relation in {"before", "after"}:
            first, second = roles.get("first", (None,))[0], roles.get("second", (None,))[0]
            if first is not None and second is not None:
                add("temporal", relation, (first if relation == "before" else second,), second if relation == "before" else first)
    return tuple(rows)


def _soft_projection(
    program: FieldProgramV2,
    vectors: VectorStore,
    relation_prototypes: dict[str, tuple[float, ...]],
    request_id: str,
    target_atom_id: str,
    scope_key: str,
    *,
    require_vectors: bool = True,
) -> tuple[tuple[SoftVariable, ...], tuple[SoftFactor, ...], tuple[DiscreteAlternative, ...], tuple[tuple[str, ...], ...]]:
    relation_by_code = {code: name for name, code in program.config.relation_codes}
    variables: dict[str, SoftVariable] = {f"c:{target_atom_id}": SoftVariable(f"c:{target_atom_id}", "confidence", 0, 1, .5)}
    variables["u:unknown"] = SoftVariable("u:unknown", "uncertainty", 0, 1, .5)
    factors: list[SoftFactor] = []
    alternatives: list[DiscreteAlternative] = []
    groups: list[tuple[str, ...]] = []
    for index, factor in enumerate(program.factors):
        relation = relation_by_code[factor.operator_code]
        context = program.contexts[factor.context_index]
        if context.scope_key != scope_key:
            applicable = False
        else:
            applicable = True
        roles = _roles(program, index)
        claim = (roles.get("claim") or roles.get("effect") or roles.get("conclusion") or (target_atom_id,))[0]
        variable_id = f"c:{claim}"
        if relation in {"supports", "opposes", "causes_hypothetically", "uncertainty"}:
            variables.setdefault(variable_id, SoftVariable(variable_id, "confidence", 0, 1, .5))
            target = context.confidence if relation in {"supports", "causes_hypothetically"} else 1.0 - context.confidence if relation == "opposes" else context.confidence
            if relation == "uncertainty":
                variable_id, target = "u:unknown", context.confidence
            binding_rows = program.bindings[factor.binding_start : factor.binding_start + factor.binding_count]
            binding_vectors = [item.binding_vector for item in binding_rows]
            if require_vectors and any(item is None for item in binding_vectors):
                raise ValueError("SOFT_VECTOR_MISSING")
            prototype = relation_prototypes.get(relation)
            if prototype is None:
                raise ValueError("FIELD_PROTOTYPE_MISSING")
            cosines = []
            for reference in binding_vectors:
                if reference is None:
                    continue
                value = np.asarray(vectors.row(reference), dtype=np.float64)
                proto = np.asarray(prototype, dtype=np.float64)
                cosines.append(float(value @ proto / max(1e-12, np.linalg.norm(value) * np.linalg.norm(proto))))
            geometry = min(1.25, max(.75, 1.0 + .25 * (sum(cosines) / max(1, len(cosines)))))
            factors.append(SoftFactor(f"{factor.factor_id}:soft", "uncertainty" if relation == "uncertainty" else "evidence", (variable_id,), (target,), factor.base_weight * geometry, context.authority, context.confidence, factor.factor_id, None, applicable))
        elif relation == "prefers":
            response = (roles.get("response") or (target_atom_id,))[0]
            variable_id = f"p:{response}"
            variables.setdefault(variable_id, SoftVariable(variable_id, "preference", 0, 1, .5))
            factors.append(SoftFactor(f"{factor.factor_id}:preference", "preference", (variable_id,), (1.0 if context.polarity == "positive" else 0.0,), factor.base_weight, context.authority, context.confidence, factor.factor_id, None, applicable))
        elif relation == "refers_to":
            mention = (roles.get("mention") or ("unknown",))[0]
            entity_ids = roles.get("entity", ())
            candidate_ids = []
            for entity in entity_ids:
                variable_id = f"r:{mention}:{entity}"
                variables.setdefault(variable_id, SoftVariable(variable_id, "reference", 0, 1, .5, f"r:{mention}"))
                candidate_ids.append(variable_id)
                factors.append(SoftFactor(f"{factor.factor_id}:{entity}", "reference", (variable_id,), (1.0,), factor.base_weight, context.authority, context.confidence, factor.factor_id, entity, applicable))
            if candidate_ids:
                groups.append(tuple(candidate_ids))
                alternatives.extend(DiscreteAlternative(entity, "reference", (item,)) for entity, item in zip(entity_ids, candidate_ids, strict=True))
    # A neutral prior keeps every projected variable strictly convex, matching G7.
    for variable in variables.values():
        kind = variable.variable_type if variable.variable_type in {"reference", "preference", "uncertainty"} else "evidence"
        factors.append(SoftFactor(f"{request_id}:prior:{variable.variable_id}", kind, (variable.variable_id,), (.5,), 4.0, 1.0, 1.0, "src:prior"))
    return tuple(sorted(variables.values(), key=lambda item: item.variable_id)), tuple(sorted(factors, key=lambda item: item.factor_id)), tuple(alternatives), tuple(groups)


def build_execution_view(
    program: FieldProgramV2,
    vectors: VectorStore,
    relation_prototypes: dict[str, tuple[float, ...]],
    request: ExecutionRequest,
    field_semantic_sha256: str,
    *,
    coverage_disposition: str = "certified",
    require_vectors: bool = True,
) -> FieldExecutionView:
    if request.target_atom_id not in {atom.atom_id for atom in program.atoms}:
        raise ValueError("TARGET_ATOM_MISSING")
    rules = tuple(rule for _id, rule in _rule_rows(program))
    target = request.target_atom_id
    facts = tuple(sorted({atom.atom_id for atom in program.atoms if atom.atom_id not in {rule.conclusion for rule in rules if rule.conclusion}}))
    g6_family = "exclusion" if any(rule.kind == "excludes" for rule in rules) else "canonical-v2"
    g6 = ReasoningProblem(request.request_id, g6_family, facts, rules, target, request.scope_key)
    variables, factors, alternatives, groups = _soft_projection(program, vectors, relation_prototypes, request.request_id, target, request.scope_key, require_vectors=require_vectors)
    family = "exclusion" if any(rule.kind == "excludes" for rule in rules) else "canonical-v2"
    g7 = ReconciliationProblem(request.request_id, family, g6, variables, factors, alternatives, groups)
    return FieldExecutionView(field_semantic_sha256, tuple(atom.atom_id for atom in program.atoms), tuple(factor.factor_id for factor in program.factors), coverage_disposition, g6, g7)


def execute_hard(view: FieldExecutionView):
    return execute(view.g6_problem)


def surface_claim(archive: SourceArchive, atom_id: str) -> SurfaceClaimRecord:
    for item in archive.surface_claims:
        if item.claim_atom_id == atom_id:
            return item
    raise ValueError("SURFACE_CLAIM_MISSING")


def g3_addresses(program: FieldProgramV2) -> tuple[TopologyAddress, ...]:
    """Project numeric atoms into the registered bounded G3 address view."""
    kind_by_code = {code: name for name, code in program.config.node_kind_codes}
    output = []
    for atom in program.atoms:
        context = program.contexts[atom.context_index]
        output.append(TopologyAddress(atom.atom_id, atom.atom_id, kind_by_code[atom.kind_code], atom.atom_id, (), None, None, context.scope_key, context.valid_from, context.valid_to, None, kind_by_code[atom.kind_code], (program.provenances[atom.provenance_index].source_key,)))
    return tuple(sorted(output, key=lambda item: item.address_id))


def g4_factors(program: FieldProgramV2) -> tuple[FrontierFactor, ...]:
    relation_by_code = {code: name for name, code in program.config.relation_codes}
    output = []
    for index, factor in enumerate(program.factors):
        bindings = program.bindings[factor.binding_start : factor.binding_start + factor.binding_count]
        context = program.contexts[factor.context_index]
        output.append(FrontierFactor(factor.factor_id, relation_by_code[factor.operator_code], tuple(program.atoms[item.atom_index].atom_id for item in bindings), (), context.scope_key, context.valid_from, context.valid_to, None, relation_by_code[factor.operator_code] in {"implies", "conjoins", "equals", "before", "after", "derived_from", "assistant_derived_from"}, False, False, None, round(context.confidence, 7), round(context.authority, 7), tuple(program.provenances[factor.provenance_index].source_key for _ in (0,))))
    return tuple(sorted(output, key=lambda item: item.factor_id))


def g5_coverage(program: FieldProgramV2, request_id: str, conclusion: str = "unknown") -> CoverageCertificate:
    regions = tuple(f"region:{factor.region_index}" for factor in program.factors)
    return CoverageCertificate(request_id, regions, (), "0" * 64, (), ("hard",), ("exception",), (), (), (), (), (), conclusion, (), 0.0, 0.0, "certified", (), 0, len(program.factors), False)
