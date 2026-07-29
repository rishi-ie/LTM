"""Deterministic conversion of supported local files into text records."""

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from ltm_poc.config import TEXT_SUFFIXES
from ltm_poc.schemas import TextRecord

STRUCTURED_SUFFIXES = {".json", ".jsonl", ".csv"}


@dataclass(frozen=True)
class IngestResult:
    records: list[TextRecord]
    skipped_files: list[str]


def _is_hidden(path: Path, root: Path) -> bool:
    return any(part.startswith(".") for part in path.relative_to(root).parts)


def _canonical_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (str, int, float)):
        return str(value)
    raise ValueError(f"unsupported JSON scalar: {type(value).__name__}")


def _flatten_json(value: Any, path: str = "") -> list[str]:
    if isinstance(value, dict):
        lines: list[str] = []
        for key in sorted(value):
            child_path = f"{path}.{key}".strip(".")
            lines.extend(_flatten_json(value[key], child_path))
        return lines
    if isinstance(value, list):
        lines = []
        for index, item in enumerate(value):
            child_path = f"{path}.{index}".strip(".")
            lines.extend(_flatten_json(item, child_path))
        return lines
    return [f"{path}: {_canonical_scalar(value)}"]


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _source_kind(suffix: str) -> str:
    if suffix == ".md":
        return "markdown"
    if suffix == ".json":
        return "json"
    if suffix == ".jsonl":
        return "jsonl"
    if suffix == ".csv":
        return "csv"
    return "text" if suffix in {".txt", ".rst"} else "source"


def _record(relative_path: str, source_kind: str, index: int, text: str) -> TextRecord:
    return TextRecord(
        record_id=f"{relative_path}::{index:06d}",
        source_path=relative_path,
        source_kind=source_kind,
        text=text,
        metadata={"record_index": index},
        content_hash=_hash_text(text),
    )


def _records_for_file(path: Path, relative_path: str) -> Iterable[TextRecord]:
    suffix = path.suffix.lower()
    source_kind = _source_kind(suffix)
    content = path.read_text(encoding="utf-8")
    if suffix in TEXT_SUFFIXES:
        yield _record(relative_path, source_kind, 0, content)
        return
    if suffix == ".json":
        value = json.loads(content)
        values = value if isinstance(value, list) else [value]
        for index, item in enumerate(values):
            text = "\n".join(_flatten_json(item))
            yield _record(relative_path, source_kind, index, text)
        return
    if suffix == ".jsonl":
        lines = (line for line in content.splitlines() if line.strip())
        for index, line in enumerate(lines):
            text = "\n".join(_flatten_json(json.loads(line)))
            yield _record(relative_path, source_kind, index, text)
        return
    if suffix == ".csv":
        for index, row in enumerate(csv.DictReader(content.splitlines())):
            lines = [f"{key}: {value}" for key, value in row.items()]
            yield _record(relative_path, source_kind, index, "\n".join(lines))


def ingest(source: Path, max_bytes: int = 10 * 1024 * 1024) -> IngestResult:
    """Read a file or directory without following symlinks or hidden paths."""
    source = source.resolve()
    root = source if source.is_dir() else source.parent
    candidates = [source] if source.is_file() else sorted(root.rglob("*"))
    records: list[TextRecord] = []
    skipped_files: list[str] = []
    for path in candidates:
        if not path.is_file() or path.is_symlink() or _is_hidden(path, root):
            continue
        relative_path = path.relative_to(root).as_posix()
        if path.suffix.lower() not in TEXT_SUFFIXES | STRUCTURED_SUFFIXES:
            skipped_files.append(relative_path)
            continue
        if path.stat().st_size > max_bytes:
            skipped_files.append(relative_path)
            continue
        try:
            records.extend(_records_for_file(path, relative_path))
        except (UnicodeDecodeError, ValueError, csv.Error, json.JSONDecodeError):
            skipped_files.append(relative_path)
    return IngestResult(records=records, skipped_files=skipped_files)
