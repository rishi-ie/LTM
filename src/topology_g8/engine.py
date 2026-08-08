from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

import numpy as np

from topology_g6.engine import execute
from topology_g6.schemas import ReasoningProblem, Rule
from topology_g7.energy import index, weight
from topology_g7.optimize import admissible, project
from topology_g7.schemas import ReconciliationProblem, SoftFactor, StructuredState

from .schemas import BatchedExecutionResult, BatchRequest, BlockContribution
from .store import BlockStore


@dataclass(frozen=True, slots=True)
class PreparedBlock:
    block_id: str
    facts: tuple[str, ...]
    rules: tuple[Rule, ...]
    soft_factors: tuple[SoftFactor, ...]
    provenance: tuple[str, ...]


def ordered_blocks(request: BatchRequest, order: str, seed: int) -> tuple[str, ...]:
    ids = sorted(request.selected_block_ids)
    if order == "ascending": return tuple(ids)
    if order == "descending": return tuple(reversed(ids))
    if order == "random":
        return tuple(sorted(ids, key=lambda item: hashlib.sha256(f"{seed}:{request.request_id}:{item}".encode()).hexdigest()))
    raise ValueError("UNKNOWN_BLOCK_ORDER")


def prepare(request: BatchRequest, store: BlockStore, block_ids: tuple[str, ...]) -> tuple[PreparedBlock, ...]:
    prepared: list[PreparedBlock] = []
    for ids, factors in store.iter_batches(block_ids):
        by_block = {block_id: [] for block_id in ids}
        for factor in factors:
            if request.request_id in factor.query_keys: by_block[factor.block_id].append(factor)
        for block_id in ids:
            relevant = sorted(by_block[block_id], key=lambda item: item.factor_id)
            prepared.append(PreparedBlock(block_id, tuple(item.hard_literal for item in relevant if item.factor_kind == "hard_fact" and item.hard_literal), tuple(item.hard_rule for item in relevant if item.factor_kind == "hard_rule" and item.hard_rule), tuple(item.soft_factor for item in relevant if item.factor_kind == "soft_factor" and item.soft_factor), tuple(provenance for item in relevant for provenance in item.provenance_ids)))
    return tuple(prepared)


def _problem(request: BatchRequest, prepared: tuple[PreparedBlock, ...]) -> ReasoningProblem:
    facts = tuple(sorted({fact for block in prepared for fact in block.facts}))
    rules = tuple(sorted({rule for block in prepared for rule in block.rules}, key=lambda item: item.rule_id))
    if len({rule.rule_id for rule in rules}) != len(rules): raise ValueError("DUPLICATE_RULE")
    return ReasoningProblem(request.request_id, request.family, facts, rules, request.target, request.scope)


def _soft_problem(request: BatchRequest, hard: ReasoningProblem, prepared: tuple[PreparedBlock, ...]) -> ReconciliationProblem:
    factors = tuple(sorted((factor for block in prepared for factor in block.soft_factors), key=lambda item: item.factor_id))
    return ReconciliationProblem(request.request_id, request.family, hard, request.soft_variables, factors, request.alternatives, request.reference_groups)


def _state(problem: ReconciliationProblem, values: np.ndarray, selected: str | None, retained: tuple[str, ...]) -> StructuredState:
    positions = index(problem); groups: dict[str, list[tuple[str, float]]] = {"confidence": [], "preference": [], "reference": []}; uncertainty = 0.0
    for variable in problem.soft_variables:
        value = float(values[positions[variable.variable_id]])
        if variable.variable_type == "uncertainty": uncertainty = value
        elif variable.variable_type in groups: groups[variable.variable_type].append((variable.variable_id, value))
    return StructuredState(tuple(groups["confidence"]), tuple(groups["preference"]), tuple(groups["reference"]), uncertainty, (selected,) if selected else (), retained)


def _block_contribution(values: np.ndarray, block: PreparedBlock, positions: dict[str, int], alternative: str | None) -> BlockContribution:
    gradient = np.zeros(len(values), dtype=np.float64); energy = 0.0; residuals: list[tuple[str, float]] = []
    for factor in block.soft_factors:
        if not factor.applicable or (factor.alternative_id is not None and factor.alternative_id != alternative): continue
        if factor.factor_type not in {"evidence", "preference", "reference", "branch", "uncertainty"}:
            raise ValueError("NONQUADRATIC_G8_FACTOR")
        pos = positions[factor.variable_ids[0]]; residual = values[pos] - factor.target_values[0]; term = weight(factor) * residual * residual
        gradient[pos] += 2.0 * weight(factor) * residual; energy += term; residuals.append((factor.factor_id, float(term)))
    return BlockContribution((block.block_id,), block.facts, block.rules, float(energy), tuple(float(item) for item in gradient), tuple(residuals), block.provenance)


def reduce_contributions(contributions: tuple[BlockContribution, ...]) -> tuple[float, np.ndarray, tuple[tuple[str, float], ...]]:
    ordered = tuple(sorted(contributions, key=lambda item: item.block_ids))
    dimension = len(ordered[0].gradient) if ordered else 0
    energy = math.fsum(item.energy for item in ordered)
    gradient = np.array([math.fsum(item.gradient[position] for item in ordered) for position in range(dimension)], dtype=np.float64)
    residuals = tuple(sorted(residual for item in ordered for residual in item.factor_residuals))
    return energy, gradient, residuals


def _stream_energy(values: np.ndarray, prepared: tuple[PreparedBlock, ...], positions: dict[str, int], alternative: str | None) -> tuple[float, np.ndarray, tuple[tuple[str, float], ...]]:
    contributions = tuple(_block_contribution(values, block, positions, alternative) for block in prepared)
    return reduce_contributions(contributions)


def _optimize(problem: ReconciliationProblem, prepared: tuple[PreparedBlock, ...], settings: dict, alternative: str | None) -> tuple[np.ndarray, float, tuple[tuple[str, float], ...]]:
    positions = index(problem); values = project(np.array([item.initial for item in problem.soft_variables], dtype=np.float64), problem)
    for _step in range(settings["maximum_steps"]):
        current, gradient, _ = _stream_energy(values, prepared, positions, alternative)
        if float(np.linalg.norm(gradient)) <= settings["convergence_tolerance"]: break
        rate = settings["learning_rate"]; accepted = False
        for _retry in range(settings["backtracking_retries"]):
            proposal = project(values - rate * gradient, problem); proposal_energy, _, _ = _stream_energy(proposal, prepared, positions, alternative)
            if proposal_energy <= current + settings["accepted_energy_tolerance"]:
                values = proposal; accepted = True; break
            rate *= .5
        if not accepted: raise RuntimeError("BACKTRACKING_EXHAUSTED")
    energy, _gradient, residuals = _stream_energy(values, prepared, positions, alternative)
    return values, energy, residuals


def evaluate_batched(request: BatchRequest, field_root, settings: dict, *, batch_width: int, order: str, seed: int) -> BatchedExecutionResult:
    store = BlockStore(field_root, batch_width)
    prepared = prepare(request, store, ordered_blocks(request, order, seed))
    hard_problem = _problem(request, prepared); hard_result = execute(hard_problem); soft_problem = _soft_problem(request, hard_problem, prepared)
    choices = []
    for alternative in admissible(soft_problem):
        values, energy, residuals = _optimize(soft_problem, prepared, settings, alternative)
        choices.append((energy, "" if alternative is None else alternative, alternative, values, residuals))
    choices.sort(key=lambda item: (item[0], item[1])); energy, _key, selected, values, residuals = choices[0]
    retained = tuple(item[2] for item in choices if item[0] - energy <= settings["decision_margin"] and item[2] is not None)
    state = _state(soft_problem, values, selected, retained)
    if state.uncertainty >= settings["abstention_threshold"]: disposition = "abstain"
    elif len(retained) > 1: disposition = "clarification_required" if request.family == "distributed_alternatives" else "resolved_with_tension"
    elif hard_result.conclusion == "conflict": disposition = "resolved_with_tension"
    else: disposition = "resolved"
    provenance = tuple(sorted({item for block in prepared for item in block.provenance if block.facts or block.rules}))
    return BatchedExecutionResult(request.request_id, hard_result, state, selected, retained, disposition, float(energy), residuals, provenance, store.trace())


def evaluate_reference(request: BatchRequest, field_root, settings: dict) -> BatchedExecutionResult:
    # Independent assembly path: materialize all selected raw blocks and call the existing G7 executor.
    from topology_g7.optimize import reconcile

    store = BlockStore(field_root, len(request.selected_block_ids))
    prepared = prepare(request, store, tuple(sorted(request.selected_block_ids)))
    hard_problem = _problem(request, prepared); soft_problem = _soft_problem(request, hard_problem, prepared); result = reconcile(soft_problem, settings)
    provenance = tuple(sorted({item for block in prepared for item in block.provenance if block.facts or block.rules}))
    return BatchedExecutionResult(request.request_id, result.hard_result, result.final_state, result.selected_branch, result.final_state.retained_alternatives, result.disposition, result.final_energy, result.factor_residuals, provenance, store.trace())
