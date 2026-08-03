from __future__ import annotations

import heapq
import time

from .indexes import FactorIndexes
from .schemas import ActiveFrontier, OmittedFactorRecord, ProofObligation, TraversalRequest

PRIORITY = {"session_fact": 0, "hard_constraint": 1, "exact_exception": 2, "fact": 3, "negative_fact": 3, "conjoins": 4, "requires": 5, "supersedes": 6, "excludes": 7, "bridge": 8, "implies": 9}


def _applies(factor, request: TraversalRequest) -> tuple[bool, str]:
    if factor.scope_id not in ("global", request.scope_id): return False, "scope_filtered"
    if factor.episode_id and factor.episode_id != request.episode_id: return False, "episode_filtered"
    if request.valid_at is not None and factor.valid_from is not None and request.valid_at < factor.valid_from: return False, "temporally_filtered"
    if request.valid_at is not None and factor.valid_to is not None and request.valid_at > factor.valid_to: return False, "temporally_filtered"
    return True, ""


def build_frontier(request: TraversalRequest, indexes: FactorIndexes, mode: str = "full") -> ActiveFrontier:
    began = time.perf_counter_ns(); opened: set[str] = set(); literals: set[str] = set(); obligations: list[ProofObligation] = []; omitted: list[OmittedFactorRecord] = []; blocks: set[str] = set(); queue: list[tuple[int, int, str, str]] = []; steps = 0; max_depth = 0; exhausted = False
    targets = (request.target_literal, f"not:{request.target_literal}")

    def enqueue(fid: str, depth: int, origin: str) -> None:
        factor = indexes.factors[fid]; heapq.heappush(queue, (PRIORITY.get(factor.factor_type, 10), depth, fid, origin))

    if mode != "no_session" and request.episode_id:
        for fid in indexes.sessions.get(request.episode_id, ()): enqueue(fid, 0, request.target_literal)
    for target in targets:
        for fid in indexes.by_target.get(target, ()):
            factor = indexes.factors[fid]
            if mode == "no_safety" and (factor.hard or factor.exact_exception): continue
            enqueue(fid, 0, target)
        if mode != "no_safety":
            for fid in indexes.hard.get(target, ()): enqueue(fid, 0, target)
            for fid in indexes.exceptions.get(target, ()): enqueue(fid, 0, target)

    while queue and steps < 2048:
        _, depth, fid, origin = heapq.heappop(queue); steps += 1; max_depth = max(max_depth, depth)
        if fid in opened: continue
        factor = indexes.factors[fid]; applies, reason = _applies(factor, request)
        if mode == "no_correction" and factor.factor_type == "supersedes": continue
        if mode == "no_conflict" and factor.factor_type in ("excludes", "opposes"): continue
        if not applies: omitted.append(OmittedFactorRecord(fid, origin, reason)); continue
        if depth > request.max_depth or len(opened) >= request.max_exact_factors or len(blocks | {indexes.block(fid)}) > request.max_blocks:
            omitted.append(OmittedFactorRecord(fid, origin, "budget_limited")); exhausted = True; continue
        opened.add(fid); blocks.add(indexes.block(fid)); literals.update(factor.target_ids)
        if mode == "forward_only":
            next_literals = factor.target_ids
            next_ids = [next_id for literal in next_literals for next_id in indexes.by_source.get(literal, ())]
        elif mode == "untyped_bfs":
            adjacent = factor.source_ids + factor.target_ids
            next_ids = [next_id for literal in adjacent for next_id in tuple(indexes.by_source.get(literal, ())) + tuple(indexes.by_target.get(literal, ()))]
        else:
            next_ids = [next_id for source in factor.source_ids for next_id in indexes.by_target.get(source, ())]
            if mode in ("full", "no_correction", "no_conflict"):
                for target in factor.target_ids:
                    next_ids.extend(indexes.conflicts.get(target, ()))
        for next_id in sorted(set(next_ids)):
            if mode == "no_session" and indexes.factors[next_id].session_factor: continue
            enqueue(next_id, depth + 1, fid)
        for source in factor.source_ids:
            candidates = tuple(indexes.by_target.get(source, ()))
            obligations.append(ProofObligation(f"obl:{fid}:{source}", source, fid, "backward", depth + 1, "satisfied" if candidates else "missing", candidates))

    if queue: exhausted = True
    hard = tuple(sorted(fid for fid in opened if indexes.factors[fid].hard and not indexes.factors[fid].exact_exception))
    exceptions = tuple(sorted(fid for fid in opened if indexes.factors[fid].exact_exception))
    conflicts = tuple(sorted(fid for fid in opened if indexes.factors[fid].factor_type in ("excludes", "opposes")))
    sessions = tuple(sorted(fid for fid in opened if indexes.factors[fid].session_factor))
    bridges = tuple(sorted(fid for fid in opened if indexes.factors[fid].factor_type == "bridge"))
    return ActiveFrontier(request.request_id, request.starting_entity_ids + request.starting_predicate_ids, tuple(sorted(opened)), tuple(sorted(literals)), tuple(sorted(obligations, key=lambda x: x.obligation_id)), hard, exceptions, conflicts, sessions, bridges, (), tuple(sorted(omitted, key=lambda x: (x.factor_id, x.reason))), tuple(sorted(blocks)), len(blocks) * indexes.block_size * 128, steps, max_depth, exhausted, (time.perf_counter_ns() - began) // 1000)
