"""Stable, serializable records exchanged by Phase 1 components."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

MetadataValue = str | int | float | bool | None


class TextRecord(BaseModel):
    record_id: str
    source_path: str
    source_kind: Literal["text", "markdown", "json", "jsonl", "csv", "source"]
    text: str
    metadata: dict[str, MetadataValue]
    content_hash: str


class ChunkRecord(BaseModel):
    chunk_id: str
    record_id: str
    source_path: str
    source_kind: str
    text: str
    char_start: int
    char_end: int
    token_start: int
    token_end: int
    token_count: int
    content_hash: str
    metadata: dict[str, MetadataValue]


class CorpusManifest(BaseModel):
    schema_version: Literal["1"] = "1"
    corpus_id: str
    created_at: str
    embedding_model_id: str
    embedding_revision: str
    dimension: Literal[384]
    dtype: Literal["float32"]
    document_count: int
    record_count: int
    chunk_count: int
    skipped_files: list[str]
    chunks_sha256: str
    vectors_sha256: str
    config_sha256: str


class EvidenceItem(BaseModel):
    rank: int
    chunk_id: str
    source_path: str
    score: float
    text: str


class OptimizationStep(BaseModel):
    step: int
    field_evaluations: int
    energy: float
    gradient_norm: float
    query_cosine: float
    state_delta: float
    nearest_chunk_ids: list[str]


class OptimizationResult(BaseModel):
    termination: Literal[
        "converged_energy", "converged_state", "max_steps", "hard_budget", "non_finite"
    ]
    update_steps: int
    field_evaluations: int
    initial_energy: float
    final_energy: float
    final_state: list[float]
    trace: list[OptimizationStep]


class DecodedAnswer(BaseModel):
    text: str
    citation_chunk_ids: list[str]
    decoder_model_id: str
    used_fallback: bool
    fallback_reason: str | None


class QueryRun(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    prompt: str
    corpus_id: str
    started_at: str
    initial_evidence: list[EvidenceItem]
    optimization: OptimizationResult
    final_evidence: list[EvidenceItem]
    answer: DecodedAnswer
    timings_ms: dict[str, float]
    peak_rss_mb: float
