"""Hash-bound, restart-safe state for the long G2.3 stages.

The workspace is deliberately the source of truth for progress.  A stage may be
resumed only while its implementation and inputs have exactly the same hashes;
this lets a laptop sleep or process interruption delay work without weakening a
frozen boundary.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, sort_keys=True, indent=2, default=str)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        Path(temporary_name).replace(path)
    finally:
        if Path(temporary_name).exists():
            Path(temporary_name).unlink()


@dataclass(frozen=True, slots=True)
class StageState:
    stage: str
    status: str
    input_hashes: tuple[tuple[str, str], ...]
    run_id: str
    cursor: tuple[tuple[str, int], ...] = ()
    artifacts: tuple[tuple[str, str], ...] = ()

    def matches(self, stage: str, input_hashes: dict[str, str]) -> bool:
        return self.stage == stage and self.input_hashes == tuple(sorted(input_hashes.items()))


def state_path(workspace: Path, stage: str) -> Path:
    return workspace / "state" / f"{stage}.json"


def load_stage(workspace: Path, stage: str) -> StageState | None:
    path = state_path(workspace, stage)
    if not path.exists():
        return None
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return StageState(
        stage=str(raw["stage"]),
        status=str(raw["status"]),
        input_hashes=tuple((str(key), str(value)) for key, value in raw["input_hashes"]),
        run_id=str(raw["run_id"]),
        cursor=tuple((str(key), int(value)) for key, value in raw.get("cursor", ())),
        artifacts=tuple((str(key), str(value)) for key, value in raw.get("artifacts", ())),
    )


def save_stage(workspace: Path, state: StageState) -> None:
    atomic_json(state_path(workspace, state.stage), asdict(state))


def begin_stage(workspace: Path, stage: str, input_hashes: dict[str, str], run_id: str) -> StageState:
    previous = load_stage(workspace, stage)
    if previous is not None:
        if not previous.matches(stage, input_hashes):
            raise RuntimeError(f"cannot resume {stage}: upstream hash changed")
        if previous.status == "completed":
            return previous
        return previous
    state = StageState(stage, "running", tuple(sorted(input_hashes.items())), run_id)
    save_stage(workspace, state)
    return state


def checkpoint_stage(
    workspace: Path,
    state: StageState,
    *,
    cursor: dict[str, int] | None = None,
    artifacts: dict[str, str] | None = None,
    status: str | None = None,
) -> StageState:
    updated = StageState(
        state.stage,
        status or state.status,
        state.input_hashes,
        state.run_id,
        tuple(sorted((cursor or dict(state.cursor)).items())),
        tuple(sorted((artifacts or dict(state.artifacts)).items())),
    )
    save_stage(workspace, updated)
    return updated
