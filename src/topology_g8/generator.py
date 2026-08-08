from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from topology_g6.schemas import Rule
from topology_g7.schemas import DiscreteAlternative, SoftFactor, SoftVariable

from .schemas import BatchRequest, StoredFactor
from .store import write_field

FAMILIES = (
    "cross_block_chain",
    "cross_block_conjunction",
    "correction_conflict",
    "distributed_evidence",
    "distributed_alternatives",
    "mixed",
)


def _soft(case: str, kind: str, variable: str, target: float, *, alternative: str | None = None, authority: float = 1.0, confidence: float = 1.0, base: float = 1.0) -> SoftFactor:
    return SoftFactor(
        f"{case}:{kind}:{variable}:{alternative or 'all'}:{target}",
        kind,
        (variable,),
        (target,),
        base,
        authority,
        confidence,
        f"source:{case}:{kind}",
        alternative,
        True,
    )


def _block_ids(seed: int, number: int, count: int) -> tuple[str, ...]:
    total = 256
    start = (seed + number * 47) % total
    values = [(start + step * 31) % total for step in range(count)]
    return tuple(f"block-{value:03d}" for value in values)


def _factor(case: str, kind: str, block_id: str, ordinal: int, *, literal: str | None = None, rule: Rule | None = None, soft: SoftFactor | None = None) -> StoredFactor:
    return StoredFactor(
        rule.rule_id if rule else f"{case}:{kind}:{ordinal}",
        kind,
        block_id,
        (case,),
        literal,
        rule,
        soft,
        (f"prov:{case}:{ordinal}",),
    )


def _case(seed: int, number: int, selected_count: int) -> tuple[BatchRequest, list[StoredFactor]]:
    family = FAMILIES[number % len(FAMILIES)]
    case = f"g8-{seed:x}-{number:03d}"
    target = f"{case}:goal"
    blocks = _block_ids(seed, number, selected_count)
    variables = [
        SoftVariable("c:claim", "confidence", 0, 1, .5),
        SoftVariable("p:style", "preference", 0, 1, .5),
        SoftVariable("u:unknown", "uncertainty", 0, 1, .5),
    ]
    alternatives: list[DiscreteAlternative] = []
    groups: list[tuple[str, ...]] = []
    factors: list[StoredFactor] = []
    hard: list[tuple[str | None, Rule | None]] = []
    a = f"{case}:a"; b = f"{case}:b"
    if family == "cross_block_chain" or family == "distributed_evidence":
        hard.append((a, None)); current = a
        for step in range(4):
            conclusion = target if step == 3 else f"{case}:mid:{step}"
            hard.append((None, Rule(f"{case}:r:{step}", "implies", (current,), conclusion)))
            current = conclusion
    elif family == "cross_block_conjunction":
        hard += [(a, None), (b, None), (None, Rule(f"{case}:join", "conjoins", (a, b), f"{case}:joined")), (None, Rule(f"{case}:end", "implies", (f"{case}:joined",), target))]
    elif family == "correction_conflict":
        hard += [(a, None), (f"not:{target}", None), (None, Rule(f"{case}:old", "implies", (a,), target)), (None, Rule(f"{case}:replace", "supersedes", (target, f"not:{target}"))), (None, Rule(f"{case}:need", "requires", (target, f"{case}:permit")))]
    elif family == "distributed_alternatives":
        hard += [(a, None), (None, Rule(f"{case}:r", "implies", (a,), target))]
        variables += [SoftVariable("c:branch", "confidence", 0, 1, .5), SoftVariable("r:alpha", "reference", 0, 1, .5, "refs"), SoftVariable("r:beta", "reference", 0, 1, .5, "refs")]
        left, right = f"{case}:alpha", f"{case}:beta"
        alternatives = [DiscreteAlternative(left, "branch", ("c:branch", "r:alpha")), DiscreteAlternative(right, "branch", ("c:branch", "r:beta"))]
        groups = [("r:alpha", "r:beta")]
    else:
        hard += [(a, None), (b, None), (None, Rule(f"{case}:join", "conjoins", (a, b), target)), (None, Rule(f"{case}:opp", "excludes", (target, f"not:{target}")))]
        variables += [SoftVariable("c:branch", "confidence", 0, 1, .5)]
        left, right = f"{case}:coherent", f"{case}:rival"
        alternatives = [DiscreteAlternative(left, "branch", ("c:branch",)), DiscreteAlternative(right, "branch", ("c:branch",))]
    for ordinal, (literal, rule) in enumerate(hard):
        block = blocks[ordinal % 8]
        factors.append(_factor(case, "hard_fact" if literal else "hard_rule", block, ordinal, literal=literal, rule=rule))
    soft: list[SoftFactor] = []
    for variable in variables:
        kind = "reference" if variable.variable_type == "reference" else "preference" if variable.variable_type == "preference" else "uncertainty" if variable.variable_type == "uncertainty" else "evidence"
        soft.append(_soft(case, kind, variable.variable_id, .5, base=4.0))
    if family == "distributed_evidence":
        soft += [_soft(case, "evidence", "c:claim", .85, authority=.9, confidence=.9), _soft(case, "evidence", "c:claim", .82, authority=.8, confidence=.9), _soft(case, "uncertainty", "u:unknown", .15, base=8.0)]
    elif family == "distributed_alternatives":
        left, right = alternatives[0].alternative_id, alternatives[1].alternative_id
        soft += [_soft(case, "branch", "c:branch", .9, alternative=left, authority=1, confidence=.95), _soft(case, "branch", "c:branch", .85, alternative=left, authority=.9, confidence=.9), _soft(case, "reference", "r:alpha", 1, alternative=left, authority=1, confidence=.9), _soft(case, "branch", "c:branch", .1, alternative=right, authority=.5, confidence=.8), _soft(case, "branch", "c:branch", .9, alternative=right, authority=.5, confidence=.8), _soft(case, "reference", "r:beta", 1, alternative=right, authority=.5, confidence=.8), _soft(case, "uncertainty", "u:unknown", .2, base=8.0)]
    elif family == "mixed":
        left, right = alternatives[0].alternative_id, alternatives[1].alternative_id
        soft += [_soft(case, "evidence", "c:claim", .8), _soft(case, "preference", "p:style", 1.0), _soft(case, "branch", "c:branch", .85, alternative=left, authority=1, confidence=.9), _soft(case, "branch", "c:branch", .1, alternative=right, authority=.4, confidence=.8), _soft(case, "branch", "c:branch", .9, alternative=right, authority=.4, confidence=.8), _soft(case, "uncertainty", "u:unknown", .15, base=8.0)]
    elif family == "correction_conflict":
        soft += [_soft(case, "evidence", "c:claim", .2), _soft(case, "uncertainty", "u:unknown", .3, base=8.0)]
    else:
        soft += [_soft(case, "evidence", "c:claim", .75), _soft(case, "preference", "p:style", 1.0), _soft(case, "uncertainty", "u:unknown", .2, base=8.0)]
    offset = len(hard)
    for ordinal, item in enumerate(soft):
        factors.append(_factor(case, "soft_factor", blocks[(offset + ordinal) % 12], offset + ordinal, soft=item))
    request = BatchRequest(case, family, target, "global", blocks, tuple(variables), tuple(alternatives), tuple(groups))
    return request, factors


def build_dataset(seed: int, cases: int, config: dict) -> tuple[list[BatchRequest], dict[str, list[StoredFactor]]]:
    block_count = config["field_factors"] // config["physical_block_size"]
    blocks = {f"block-{number:03d}": [] for number in range(block_count)}
    requests: list[BatchRequest] = []
    for number in range(cases):
        request, factors = _case(seed, number, config["selected_blocks_per_request"])
        requests.append(request)
        for factor in factors:
            blocks[factor.block_id].append(factor)
    for block_id, factors in blocks.items():
        while len(factors) < config["physical_block_size"]:
            slot = len(factors)
            factors.append(StoredFactor(f"distractor:{block_id}:{slot}", "hard_fact", block_id, (), f"distractor:{block_id}:{slot}", None, None, (f"prov:{block_id}:{slot}",)))
        if len(factors) > config["physical_block_size"]:
            raise ValueError("BLOCK_OVERFULL")
    return requests, blocks


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, default=str, indent=2, sort_keys=True))
    temporary.replace(path)


def materialize(root: Path, requests: list[BatchRequest], blocks: dict[str, list[StoredFactor]]) -> None:
    write_field(root / "field", blocks)
    write_json(root / "requests.json", [asdict(item) for item in requests])


def load_requests(root: Path) -> list[BatchRequest]:
    rows = json.loads((root / "requests.json").read_text())
    output = []
    for row in rows:
        variables = tuple(SoftVariable(**item) for item in row["soft_variables"])
        alternatives = tuple(DiscreteAlternative(**{**item, "affected_ids": tuple(item["affected_ids"]), "incompatible_hard_ids": tuple(item["incompatible_hard_ids"])}) for item in row["alternatives"])
        output.append(BatchRequest(row["request_id"], row["family"], row["target"], row["scope"], tuple(row["selected_block_ids"]), variables, alternatives, tuple(tuple(item) for item in row["reference_groups"])))
    return output
