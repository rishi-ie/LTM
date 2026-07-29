"""Pinned, explicit acquisition and local-only loading of Phase 1 models."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
from huggingface_hub import snapshot_download
from sentence_transformers import SentenceTransformer
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer


@dataclass(frozen=True)
class ModelSpec:
    repo_id: str
    revision: str
    directory: str
    allow_patterns: tuple[str, ...]
    ignore_patterns: tuple[str, ...]


EMBEDDING_MODEL = ModelSpec(
    repo_id="sentence-transformers/all-MiniLM-L6-v2",
    revision="1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
    directory="all-MiniLM-L6-v2",
    allow_patterns=(
        "*.json",
        "*.txt",
        "*.safetensors",
        "1_Pooling/*",
        "modules.json",
        "README.md",
    ),
    ignore_patterns=("*.bin", "*.h5", "*.ot", "*.msgpack", "onnx/*", "openvino/*"),
)
DECODER_MODEL = ModelSpec(
    repo_id="google/flan-t5-small",
    revision="0fc9ddf78a1e988dac52e2dac162b0ede4fd74ab",
    directory="flan-t5-small",
    allow_patterns=("*.json", "*.model", "*.safetensors", "README.md"),
    ignore_patterns=("*.bin", "*.h5", "*.msgpack"),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as model_file:
        for block in iter(lambda: model_file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _model_files(path: Path) -> dict[str, str]:
    return {
        str(file.relative_to(path)): _sha256(file)
        for file in sorted(path.rglob("*"))
        if file.is_file() and ".cache" not in file.relative_to(path).parts
    }


def download_models(model_dir: Path) -> dict[str, Any]:
    """Download exactly the selected revisions and save their file hashes."""
    model_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []
    for spec in (EMBEDDING_MODEL, DECODER_MODEL):
        local_dir = model_dir / spec.directory
        snapshot_download(
            repo_id=spec.repo_id,
            revision=spec.revision,
            local_dir=local_dir,
            allow_patterns=list(spec.allow_patterns),
            ignore_patterns=list(spec.ignore_patterns),
        )
        entries.append(
            {
                "repo_id": spec.repo_id,
                "revision": spec.revision,
                "directory": spec.directory,
                "files_sha256": _model_files(local_dir),
            }
        )
    manifest = {"schema_version": "1", "models": entries}
    (model_dir / "model-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def require_model_paths(model_dir: Path) -> tuple[Path, Path]:
    embedding_path = model_dir / EMBEDDING_MODEL.directory
    decoder_path = model_dir / DECODER_MODEL.directory
    missing = [
        str(path) for path in (embedding_path, decoder_path) if not path.is_dir()
    ]
    if missing:
        raise FileNotFoundError(
            "missing local model directories: "
            + ", ".join(missing)
            + "; run `ltm-poc models download --model-dir ./.models`"
        )
    return embedding_path, decoder_path


def load_embedding_model(model_path: Path, device: str) -> SentenceTransformer:
    return SentenceTransformer(
        model_name_or_path=str(model_path),
        device=device,
        trust_remote_code=False,
        local_files_only=True,
    )


def load_decoder(model_path: Path, device: str) -> tuple[Any, Any]:
    tokenizer = AutoTokenizer.from_pretrained(
        model_path,
        local_files_only=True,
        trust_remote_code=False,
    )
    model = AutoModelForSeq2SeqLM.from_pretrained(
        model_path,
        local_files_only=True,
        trust_remote_code=False,
        use_safetensors=True,
        torch_dtype=torch.float32,
    )
    return tokenizer, model.eval().to(device)


def smoke_models(model_dir: Path, device: str) -> dict[str, str | int]:
    """Run one local embedding and one deterministic decoder inference."""
    embedding_path, decoder_path = require_model_paths(model_dir)
    embedding_model = load_embedding_model(embedding_path, device)
    vector = embedding_model.encode(
        ["LTM smoke test"],
        batch_size=1,
        convert_to_numpy=True,
        normalize_embeddings=True,
        precision="float32",
        show_progress_bar=False,
    )
    tokenizer, decoder = load_decoder(decoder_path, device)
    tokenized = tokenizer("Reply with: ok", return_tensors="pt").to(device)
    with torch.inference_mode():
        output = decoder.generate(
            **tokenized,
            max_new_tokens=8,
            do_sample=False,
            num_beams=1,
            use_cache=True,
        )
    return {
        "embedding_dimension": int(vector.shape[1]),
        "decoder_output": tokenizer.decode(output[0], skip_special_tokens=True),
    }
