"""Integrity-checked local payload and vector store."""

import hashlib
import os
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from ltm_poc.config import WorkspaceConfig
from ltm_poc.schemas import ChunkRecord, CorpusManifest


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _config_sha256(config: WorkspaceConfig) -> str:
    return hashlib.sha256(config.model_dump_json().encode("utf-8")).hexdigest()


class CorpusStore:
    def __init__(self, root: Path):
        self.root = root
        self.chunks_path = root / "chunks.jsonl"
        self.vectors_path = root / "vectors.npy"
        self.manifest_path = root / "corpus-manifest.json"

    def write(
        self,
        chunks: list[ChunkRecord],
        vectors: np.ndarray,
        config: WorkspaceConfig,
    ) -> CorpusManifest:
        if vectors.shape != (len(chunks), 384) or vectors.dtype != np.float32:
            raise ValueError("vectors must be float32 with one 384-vector per chunk")
        self.root.mkdir(parents=True, exist_ok=True)
        chunks_new = self.chunks_path.with_suffix(".jsonl.new")
        vectors_new = self.vectors_path.with_suffix(".npy.new")
        chunks_new.write_text(
            "".join(chunk.model_dump_json() + "\n" for chunk in chunks),
            encoding="utf-8",
        )
        with vectors_new.open("wb") as destination:
            np.save(destination, vectors, allow_pickle=False)
        loaded_chunks = self._read_chunks(chunks_new)
        loaded_vectors = np.load(vectors_new, allow_pickle=False)
        if len(loaded_chunks) != len(chunks) or not np.array_equal(
            loaded_vectors, vectors
        ):
            raise ValueError("new corpus files failed validation")
        manifest = CorpusManifest(
            corpus_id=_sha256(chunks_new)[:16],
            created_at=datetime.now(UTC).isoformat(),
            embedding_model_id=config.embedding_model_id,
            embedding_revision=config.embedding_revision,
            dimension=384,
            dtype="float32",
            document_count=len({chunk.source_path for chunk in chunks}),
            record_count=len({chunk.record_id for chunk in chunks}),
            chunk_count=len(chunks),
            skipped_files=[],
            chunks_sha256=_sha256(chunks_new),
            vectors_sha256=_sha256(vectors_new),
            config_sha256=_config_sha256(config),
        )
        self._replace_with_backup(chunks_new, self.chunks_path)
        self._replace_with_backup(vectors_new, self.vectors_path)
        self.manifest_path.write_text(
            manifest.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )
        return manifest

    def read(self) -> tuple[list[ChunkRecord], np.ndarray, CorpusManifest]:
        chunks = self._read_chunks(self.chunks_path)
        vectors = np.load(self.vectors_path, allow_pickle=False)
        manifest = CorpusManifest.model_validate_json(
            self.manifest_path.read_text(encoding="utf-8")
        )
        if (
            vectors.shape != (len(chunks), manifest.dimension)
            or vectors.dtype != np.float32
        ):
            raise ValueError("corpus rows do not match the manifest")
        if _sha256(self.chunks_path) != manifest.chunks_sha256:
            raise ValueError("chunk payload hash does not match manifest")
        if _sha256(self.vectors_path) != manifest.vectors_sha256:
            raise ValueError("vector payload hash does not match manifest")
        return chunks, vectors, manifest

    @staticmethod
    def _read_chunks(path: Path) -> list[ChunkRecord]:
        return [
            ChunkRecord.model_validate_json(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line
        ]

    @staticmethod
    def _replace_with_backup(new_path: Path, final_path: Path) -> None:
        previous = final_path.with_suffix(final_path.suffix + ".previous")
        if final_path.exists():
            os.replace(final_path, previous)
        os.replace(new_path, final_path)
