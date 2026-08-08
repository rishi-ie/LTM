"""Atomic, hash-bound stage state for restart-safe G2.4 execution."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path


def file_hash(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            value.update(chunk)
    return value.hexdigest()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True, default=str)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


@dataclass(frozen=True, slots=True)
class StageState:
    stage: str
    status: str
    inputs: tuple[tuple[str, str], ...]
    artifacts: tuple[tuple[str, str], ...] = ()


def stage_path(workspace: Path, stage: str) -> Path:
    return workspace / "state" / f"{stage}.json"


def begin_stage(workspace: Path, stage: str, inputs: dict[str, str]) -> StageState:
    path = stage_path(workspace, stage)
    frozen = tuple(sorted(inputs.items()))
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
        current = StageState(raw["stage"], raw["status"], tuple(map(tuple, raw["inputs"])), tuple(map(tuple, raw.get("artifacts", ()))))
        if current.inputs != frozen:
            raise RuntimeError(f"cannot resume {stage}: inputs changed")
        return current
    current = StageState(stage, "running", frozen)
    atomic_json(path, asdict(current))
    return current


def complete_stage(workspace: Path, state: StageState, artifacts: dict[str, str]) -> StageState:
    completed = StageState(state.stage, "completed", state.inputs, tuple(sorted(artifacts.items())))
    atomic_json(stage_path(workspace, state.stage), asdict(completed))
    return completed
