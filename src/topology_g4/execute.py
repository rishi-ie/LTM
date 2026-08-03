from __future__ import annotations

from .schemas import FrontierExecutionResult, TopologyFactor, TraversalRequest


def execute(request: TraversalRequest, factors: tuple[TopologyFactor, ...]) -> FrontierExecutionResult:
    applicable = [factor for factor in factors if factor.scope_id in ("global", request.scope_id) and (not factor.episode_id or factor.episode_id == request.episode_id) and (factor.valid_from is None or request.valid_at is None or request.valid_at >= factor.valid_from) and (factor.valid_to is None or request.valid_at is None or request.valid_at <= factor.valid_to)]
    active: set[str] = set(); proof: set[str] = set(); conflicts: set[str] = set()
    for factor in applicable:
        if factor.factor_type in ("fact", "negative_fact", "session_fact", "hard_constraint", "exact_exception"):
            active.update(factor.target_ids); proof.add(factor.factor_id)
    for factor in applicable:
        if factor.factor_type == "supersedes" and len(factor.source_ids) >= 2 and factor.source_ids[1] in active:
            active.discard(factor.source_ids[0]); proof.add(factor.factor_id)
        elif factor.factor_type == "exact_exception" and factor.target_ids and factor.target_ids[0].startswith("not:"):
            active.discard(factor.target_ids[0][4:])
    changed = True
    while changed:
        changed = False
        for factor in applicable:
            if factor.factor_type in ("implies", "conjoins", "requires", "bridge") and all(source in active for source in factor.source_ids):
                before = len(active); active.update(factor.target_ids); proof.add(factor.factor_id)
                if len(active) != before: changed = True
            elif factor.factor_type == "supersedes" and all(source in active for source in factor.source_ids): proof.add(factor.factor_id)
            elif factor.factor_type in ("excludes", "opposes") and request.target_literal in factor.target_ids and all(source in active for source in factor.source_ids): conflicts.add(factor.factor_id); proof.add(factor.factor_id)
    for factor in applicable:
        if factor.factor_type == "supersedes" and len(factor.source_ids) >= 2 and factor.source_ids[1] in active:
            active.discard(factor.source_ids[0])
    for factor in applicable:
        if factor.factor_type == "exact_exception" and factor.target_ids and factor.target_ids[0].startswith("not:"):
            active.discard(factor.target_ids[0][4:])
    positive = request.target_literal in active; negative = f"not:{request.target_literal}" in active
    conclusion = "conflict" if conflicts or (positive and negative) else "entailed" if positive else "contradicted" if negative else "unknown"
    used = tuple(sorted(proof)); provenance = tuple(sorted(p for factor in applicable if factor.factor_id in proof for p in factor.provenance_ids))
    return FrontierExecutionResult(request.request_id, conclusion, used, provenance, tuple(sorted(conflicts)), ())
