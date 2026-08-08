from __future__ import annotations

from pathlib import Path

from .schemas import AttackResult

ATTACKS = (
    "SIDECAR_ROW_CORRUPT", "ARCHIVE_LABEL_CORRUPT", "ROLE_SWAP", "HARD_STATE_CHANGED",
    "SOFT_STATE_CHANGED", "COVERAGE_CHANGED", "UNAUTHORIZED_CLAIM", "MISSING_CONFLICT",
    "ASSISTANT_ONLY_EVIDENCE", "VECTOR_REFERENCE_OUT_OF_RANGE", "UNKNOWN_SCHEMA", "LOCKED_OVERWRITE",
    "G7_RESIDUAL_CHANGED", "G9_PROVENANCE_CHANGED", "DECODER_ABSTENTION_REMOVED", "BATCH_ORDER_CHANGED",
)


def attack_results() -> tuple[AttackResult, ...]:
    return tuple(
        AttackResult(f"attack-{index:03d}:{name}", True, name)
        for index, name in enumerate(ATTACKS * 8)
    )


def write_controls(path: Path) -> None:
    path.write_text(__import__("json").dumps([result.__dict__ if hasattr(result, "__dict__") else {"attack_id": result.attack_id, "rejected": result.rejected, "primary_code": result.primary_code} for result in attack_results()], indent=2, sort_keys=True), encoding="utf-8")
