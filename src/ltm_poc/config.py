"""Validated workspace configuration."""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

TEXT_SUFFIXES = {
    ".txt",
    ".md",
    ".rst",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".java",
    ".go",
    ".rs",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".html",
    ".css",
    ".yaml",
    ".yml",
    ".toml",
}


class WorkspaceConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: Literal["1"] = "1"
    embedding_model_path: str = Field(min_length=1)
    embedding_model_id: str = Field(min_length=1)
    embedding_revision: str = Field(min_length=1)
    decoder_model_path: str = Field(min_length=1)
    decoder_model_id: str = Field(min_length=1)
    decoder_revision: str = Field(min_length=1)
    device: Literal["auto", "cpu", "mps"] = "auto"
    chunk_wordpieces: int = Field(default=128, gt=0)
    chunk_overlap_wordpieces: int = Field(default=24, ge=0)
    embedding_batch_size: int = Field(default=32, gt=0)
    active_candidates: int = Field(default=128, gt=0)
    evidence_limit: int = Field(default=4, gt=0)
    query_temperature: float = Field(default=0.05, gt=0)
    field_temperature: float = Field(default=0.10, gt=0)
    query_anchor: float = Field(default=1.0, gt=0)
    optimizer_learning_rate: float = Field(default=0.05, gt=0)
    optimizer_max_steps: int = Field(default=8, gt=0)
    optimizer_hard_evaluations: int = Field(default=16, gt=0)
    energy_tolerance: float = Field(default=1e-4, gt=0)
    state_tolerance: float = Field(default=1e-4, gt=0)
    convergence_patience: int = Field(default=2, gt=0)
    decoder_excerpt_tokens: int = Field(default=80, gt=0)
    decoder_input_tokens: int = Field(default=512, gt=0)
    decoder_output_tokens: int = Field(default=128, gt=0)
    seed: int = 1729

    @model_validator(mode="after")
    def validate_budgets(self) -> "WorkspaceConfig":
        if self.chunk_overlap_wordpieces >= self.chunk_wordpieces:
            raise ValueError(
                "chunk_overlap_wordpieces must be smaller than chunk_wordpieces"
            )
        if self.evidence_limit > self.active_candidates:
            raise ValueError("evidence_limit cannot exceed active_candidates")
        if self.optimizer_max_steps + 1 > self.optimizer_hard_evaluations:
            raise ValueError(
                "optimizer_max_steps plus final evaluation exceeds hard budget"
            )
        return self


def load_workspace_config(path: Path) -> WorkspaceConfig:
    """Load a workspace config and resolve its model paths against its location."""
    with path.open(encoding="utf-8") as config_file:
        config = WorkspaceConfig.model_validate(json.load(config_file))
    base = path.parent.resolve()
    return config.model_copy(
        update={
            "embedding_model_path": str((base / config.embedding_model_path).resolve()),
            "decoder_model_path": str((base / config.decoder_model_path).resolve()),
        }
    )


def write_workspace_config(path: Path, config: WorkspaceConfig) -> None:
    """Write a canonical JSON config; callers control directory creation."""
    path.write_text(config.model_dump_json(indent=2) + "\n", encoding="utf-8")
