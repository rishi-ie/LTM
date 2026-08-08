from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from .schemas import QueryCase, Scale


def stable_int(*parts: object) -> int:
    payload = "\x1f".join(str(part) for part in parts).encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def scales(settings: dict) -> tuple[Scale, ...]:
    chunks = []
    for number, tokens in enumerate(settings["scale_tokens"], start=1):
        count = tokens // settings["tokens_per_chunk"]
        factors = count * settings["factors_per_chunk"]
        blocks = math.ceil(factors / settings["factor_block_size"])
        chunks.append(Scale(f"S{number}", tokens, count, factors, blocks, math.ceil(blocks / settings["region_block_count"])))
    return tuple(chunks)


FAMILIES = (
    "direct",
    "chain",
    "conjunction_requirement",
    "correction",
    "constraint_exception",
    "conflict",
    "session_episode",
    "distant_bridge",
    "unsupported_ambiguous",
)


def cases(seed: int, count: int, *, development: bool) -> tuple[QueryCase, ...]:
    """Create query semantics independent of scale; every core factor lives in S1."""
    output: list[QueryCase] = []
    core_blocks = 900 if development else 960
    for number in range(count):
        family = FAMILIES[number % len(FAMILIES)]
        outcome = ("entailed", "contradicted", "unknown", "conflict")[number % 4]
        if family == "unsupported_ambiguous":
            outcome = "unknown"
        depth = 1 + stable_int(seed, "depth", number) % 6
        local = stable_int(seed, "local", number) % 128
        extra = tuple(sorted({local} | {128 + stable_int(seed, "rule", number, step) % 512 for step in range(depth)}))
        remote = None
        if family in {"distant_bridge", "constraint_exception", "correction", "conflict"}:
            remote = 640 + stable_int(seed, "remote", number) % (core_blocks - 640)
            extra = tuple(sorted(set(extra) - {remote}))
        output.append(QueryCase(
            query_id=f"{'dev' if development else 'locked'}-{number:04d}", family=family, gold=outcome,
            depth=depth, target=f"target-{seed:x}-{number:04d}", scope="fictional" if number % 11 == 0 else "global",
            episode_id=f"episode-{number % 32:02d}" if family == "session_episode" else None,
            required_blocks=extra, remote_block=remote, has_constraint=family == "constraint_exception",
            has_exception=family == "constraint_exception", session_overlay=family == "session_episode",
        ))
    return tuple(output)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True))
    temporary.replace(path)


def load_cases(path: Path) -> tuple[QueryCase, ...]:
    return tuple(QueryCase(**value) for value in json.loads(path.read_text()))
