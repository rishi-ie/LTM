from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np

from .dataset import generate_cases

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / ".models" / "all-MiniLM-L6-v2"
EXPECTED = {
    "config.json": "953f9c0d463486b10a6871cc2fd59f223b2c70184f49815e7efbcab5d8908b41",
    "model.safetensors": "53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db",
    "tokenizer.json": "be50c3628f2bf5bb5e3a7f17b1f74611b2561a3a27eeab05e5aa30f411572037",
}


def model_hashes() -> dict[str, str]:
    return {name: hashlib.sha256((MODEL / name).read_bytes()).hexdigest() for name in EXPECTED}


def model_check() -> dict:
    hashes = model_hashes()
    if hashes != EXPECTED:
        raise RuntimeError("frozen MiniLM hash mismatch")
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(str(MODEL), local_files_only=True, device="cpu")
    first = model.encode(["Vora is amber."], normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)[0]
    second = model.encode(["Vora is amber."], normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)[0]
    return {"hashes": hashes, "dimension": int(first.shape[0]), "identical": bool(np.allclose(first, second, atol=1e-7)), "norm": float(np.linalg.norm(first))}


def encode_split(split: str, workspace: Path) -> Path:
    cases = generate_cases(split)
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(str(MODEL), local_files_only=True, device="cpu")
    texts = [case.statement for case in cases] + [arg.text for case in cases for arg in case.arguments]
    vectors = model.encode(texts, batch_size=128, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False).astype(np.float32)
    n = len(cases)
    statement = vectors[:n]
    args = np.zeros((n, 3, 384), dtype=np.float32)
    mask = np.zeros((n, 3), dtype=np.float32)
    cursor = n
    for row, case in enumerate(cases):
        for slot, _ in enumerate(case.arguments):
            args[row, slot] = vectors[cursor]
            mask[row, slot] = 1
            cursor += 1
    if not np.allclose(np.linalg.norm(statement, axis=1), 1, atol=1e-5):
        raise RuntimeError("embedding normalization failure")
    out = workspace / split / "embeddings.npz"
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out, statement=statement, arguments=args, mask=mask)
    manifest = {"split": split, "cases": n, "hashes": model_hashes(), "shape": list(statement.shape)}
    (workspace / split / "embedding-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return out
