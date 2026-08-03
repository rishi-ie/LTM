from __future__ import annotations

import json
import random
from dataclasses import asdict
from pathlib import Path

from .schemas import TopologyFactor, TraversalRequest, canonical_hash

FAMILIES = ("chain", "conjunction", "temporal", "conflict", "exception", "session_bridge")


def _factor(fid: str, kind: str, sources: tuple[str, ...], targets: tuple[str, ...], **kwargs) -> TopologyFactor:
    return TopologyFactor(fid, kind, sources, targets, provenance_ids=(f"prov:{fid}",), **kwargs)


def _problem(seed: int, index: int, family: str) -> tuple[list[TopologyFactor], TraversalRequest, dict]:
    prefix = f"p{seed:x}-{index:04d}"
    depth = index % 6 + 1
    target = f"{prefix}:target"
    negative = f"not:{target}"
    factors: list[TopologyFactor] = []
    required: list[str] = []
    current = f"{prefix}:fact0"
    fact = _factor(f"{prefix}:f0", "fact", (), (current,))
    factors.append(fact); required.append(fact.factor_id)
    for step in range(depth):
        destination = target if step == depth - 1 else f"{prefix}:step{step+1}"
        rule = _factor(f"{prefix}:r{step}", "implies", (current,), (destination,))
        factors.append(rule); required.append(rule.factor_id); current = destination

    conclusion = "entailed"
    hard: list[str] = []; exceptions: list[str] = []; sessions: list[str] = []; bridges: list[str] = []; conflicts: list[str] = []
    if family == "conjunction":
        extra_lit = f"{prefix}:extra"
        extra = _factor(f"{prefix}:extra-fact", "fact", (), (extra_lit,))
        conjunction = _factor(f"{prefix}:conjoin", "conjoins", (target, extra_lit), (f"{prefix}:joined",))
        requirement = _factor(f"{prefix}:require", "requires", (extra_lit,), (f"{prefix}:joined",))
        factors.extend((extra, conjunction, requirement)); required.extend((extra.factor_id, conjunction.factor_id, requirement.factor_id)); target = f"{prefix}:joined"
    elif family == "temporal":
        newer = _factor(f"{prefix}:newer", "negative_fact", (), (negative,), valid_from=50)
        supersedes = _factor(f"{prefix}:supersede", "supersedes", (target, negative), (target,))
        factors.extend((newer, supersedes)); required.extend((newer.factor_id, supersedes.factor_id)); conclusion = "contradicted"
    elif family == "conflict":
        opposing = _factor(f"{prefix}:opposing", "negative_fact", (), (negative,))
        exclusion = _factor(f"{prefix}:exclude", "excludes", (target, negative), (target,))
        factors.extend((opposing, exclusion)); required.extend((opposing.factor_id, exclusion.factor_id)); conflicts.append(exclusion.factor_id); conclusion = "conflict"
    elif family == "exception":
        exception = _factor(f"{prefix}:exception", "exact_exception", (), (negative,), hard=True, exact_exception=True)
        factors.append(exception); required.append(exception.factor_id); exceptions.append(exception.factor_id); conclusion = "contradicted"
    elif family == "session_bridge":
        session_lit = f"{prefix}:session"
        session = _factor(f"{prefix}:session", "session_fact", (), (session_lit,), episode_id=f"episode-{index}", session_factor=True)
        bridge = _factor(f"{prefix}:bridge", "bridge", (session_lit,), (target,), episode_id=f"episode-{index}", bridge_region_id=f"region-{index}")
        factors.extend((session, bridge)); required.extend((session.factor_id, bridge.factor_id)); sessions.append(session.factor_id); bridges.append(bridge.factor_id)
    if index % 10 == 0:
        constraint = _factor(f"{prefix}:hard", "hard_constraint", (), (target,), hard=True)
        factors.append(constraint); required.append(constraint.factor_id); hard.append(constraint.factor_id)

    request = TraversalRequest(prefix, (f"entity:{prefix}",), (f"predicate:{prefix}",), target, "global", 60, f"episode-{index}" if family == "session_bridge" else None, "positive")
    gold = {"request_id": prefix, "family": family, "required_factor_ids": sorted(required), "required_hard_constraint_ids": hard, "required_exception_ids": exceptions, "required_session_factor_ids": sessions, "required_bridge_ids": bridges, "required_conflict_ids": conflicts, "decisive_provenance_ids": sorted(p for factor in factors if factor.factor_id in required for p in factor.provenance_ids), "gold_conclusion": conclusion, "gold_proof_depth": depth}
    return factors, request, gold


def build_dataset(seed: int, factor_count: int, case_count: int) -> tuple[tuple[TopologyFactor, ...], list[dict], list[dict]]:
    factors: list[TopologyFactor] = []; requests: list[dict] = []; gold: list[dict] = []
    for index in range(case_count):
        family = FAMILIES[index % len(FAMILIES)]
        problem, request, answer = _problem(seed, index, family)
        factors.extend(problem); requests.append(asdict(request)); gold.append(answer)
    rng = random.Random(seed)
    while len(factors) < factor_count:
        i = len(factors); source = f"d{seed:x}:{rng.randrange(10000)}"; target = f"d{seed:x}:{rng.randrange(10000)}"
        factors.append(_factor(f"distractor:{seed}:{i:06d}", "implies", (source,), (target,), scope_id=f"scope-{i % 20}"))
    return tuple(factors[:factor_count]), requests, gold


def validate_required_factors(factors: tuple[TopologyFactor, ...], requests: list[dict], gold: list[dict]) -> None:
    """Confirm generated gold is executable and every registered factor contributes to its proof."""
    from .execute import execute

    by_id = {factor.factor_id: factor for factor in factors}
    for request_row, gold_row in zip(requests, gold):
        request = TraversalRequest(**{**request_row, "starting_entity_ids": tuple(request_row["starting_entity_ids"]), "starting_predicate_ids": tuple(request_row["starting_predicate_ids"])})
        required = tuple(by_id[fid] for fid in gold_row["required_factor_ids"])
        result = execute(request, required)
        if result.conclusion != gold_row["gold_conclusion"]:
            raise RuntimeError(f"generator oracle mismatch: {request.request_id}")
        if not set(gold_row["required_factor_ids"]).issubset(result.proof_factor_ids):
            raise RuntimeError(f"non-contributing required factor: {request.request_id}")
        for removed in gold_row["required_factor_ids"]:
            reduced = tuple(factor for factor in required if factor.factor_id != removed)
            changed = execute(request, reduced)
            if changed.conclusion == result.conclusion and changed.proof_factor_ids == result.proof_factor_ids and changed.conflicts == result.conflicts:
                raise RuntimeError(f"leave-one-out factor had no registered effect: {removed}")


def write_jsonl(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def manifest(factors: tuple[TopologyFactor, ...]) -> dict:
    return {"factor_count": len(factors), "topology_hash": canonical_hash([asdict(item) for item in factors]), "blocks": (len(factors) + 255) // 256}
