"""Reversible archive of local, ignored research artifacts.

The archive is intentionally a filesystem concern, not part of the semantic
source/archive plane.  Only top-level artifacts selected by the frozen plan
are moved; all operations are write-once and journaled.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

PLAN_RELATIVE = Path("workspaces/_repository-catalog/archive-plan.json")
POINTER_RELATIVE = Path("workspaces/_repository-catalog/archive-pointer.json")
DEFAULT_MIN_BYTES = 100 * 1024 * 1024
_HASH_NAMES = {"frozen-manifest.json", "locked-results.json", "report.json", "verification.json"}


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _inventory(path: Path, *, hash_all: bool = False, allow_symlinks: bool = False) -> dict[str, Any]:
    if path.is_symlink():
        raise RuntimeError(f"symlink is not archivable: {path}")
    files = 0
    directories = 0
    logical_bytes = 0
    selected: dict[str, str] = {}
    symlinks: dict[str, str] = {}
    for current, dirnames, filenames in os.walk(path, topdown=True, followlinks=False):
        current_path = Path(current)
        safe_dirs = []
        for name in sorted(dirnames):
            child = current_path / name
            if child.is_symlink():
                if not allow_symlinks:
                    raise RuntimeError(f"symlink is not archivable: {child}")
                symlinks[str(child.relative_to(path))] = os.readlink(child)
                continue
            safe_dirs.append(name)
        dirnames[:] = safe_dirs
        directories += len(safe_dirs)
        for name in sorted(filenames):
            child = current_path / name
            if child.is_symlink():
                if not allow_symlinks:
                    raise RuntimeError(f"symlink is not archivable: {child}")
                symlinks[str(child.relative_to(path))] = os.readlink(child)
                continue
            size = child.stat().st_size
            files += 1
            logical_bytes += size
            relative = str(child.relative_to(path))
            if hash_all or child.name in _HASH_NAMES or child.name == "selected-kernel.pt":
                selected[relative] = sha256(child)
    root_stat = path.stat()
    return {
        "logical_bytes": logical_bytes,
        "file_count": files,
        "directory_count": directories,
        "root_device": root_stat.st_dev,
        "root_inode": root_stat.st_ino,
        "selected_hashes": selected,
        "symlinks": symlinks,
    }


def _directory_size(path: Path) -> int:
    return int(_inventory(path)["logical_bytes"])


def _authorities(root: Path) -> dict[str, str]:
    registry_path = root / "docs/experiments/registry.json"
    if not registry_path.exists():
        return {}
    rows = _read_json(registry_path).get("experiments", [])
    return {
        row["authoritative_workspace"]: row["experiment_id"]
        for row in rows if row.get("authoritative_workspace")
    }


def _model_allowlist(root: Path) -> set[str]:
    manifest = root / ".models/model-manifest.json"
    if not manifest.exists():
        raise RuntimeError(".models/model-manifest.json is required before archiving models")
    value = _read_json(manifest)
    names: set[str] = set()
    records = value.get("models", value.get("entries", []))
    if isinstance(records, dict):
        records = records.values()
    for record in records:
        if isinstance(record, str):
            names.add(Path(record).name)
        elif isinstance(record, dict):
            for key in ("path", "relative_path", "name", "directory"):
                if record.get(key):
                    names.add(Path(str(record[key])).name)
                    break
    return names


def _entry(root: Path, source_relative: str, archive_relative: str, kind: str,
           *, authorities: dict[str, str]) -> dict[str, Any]:
    source = root / source_relative
    stats = _inventory(source, hash_all=kind == "model", allow_symlinks=kind == "environment")
    return {
        "kind": kind,
        "source_relative": source_relative,
        "archive_relative": archive_relative,
        **stats,
        "authoritative_for": authorities.get(source_relative),
        "disposition": "authoritative" if source_relative in authorities else "historical-preserved",
        "status": "planned",
    }


def build_plan(root: Path, destination: Path, min_workspace_mib: int = 100) -> dict[str, Any]:
    destination = destination.expanduser().absolute()
    workspace_root = root / "workspaces"
    threshold = min_workspace_mib * 1024 * 1024
    authorities = _authorities(root)
    entries: list[dict[str, Any]] = []
    for source in sorted(workspace_root.iterdir()):
        if not source.is_dir() or source.name == "_repository-catalog" or source.is_symlink():
            continue
        if _directory_size(source) >= threshold:
            relative = str(source.relative_to(root))
            entries.append(_entry(root, relative, relative, "workspace", authorities=authorities))
    historical_env = root / ".venv-g101"
    if historical_env.exists():
        entries.append(_entry(root, ".venv-g101", "environments/.venv-g101", "environment", authorities=authorities))
    model_root = root / ".models"
    allowlist = _model_allowlist(root)
    for model in sorted(model_root.iterdir()) if model_root.exists() else []:
        if model.is_dir() and model.name not in allowlist and model.name != "model-manifest.json":
            entries.append(_entry(root, str(model.relative_to(root)), f"models/{model.name}", "model", authorities=authorities))
    totals = {
        "entries": len(entries),
        "logical_bytes": sum(item["logical_bytes"] for item in entries),
        "file_count": sum(item["file_count"] for item in entries),
        "directory_count": sum(item["directory_count"] for item in entries),
    }
    return {
        "archive_revision": "pre-prototype-archive-v1",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_root": str(root.absolute()),
        "destination": str(destination),
        "min_workspace_mib": min_workspace_mib,
        "min_workspace_bytes": threshold,
        "selection": {
            "workspace_directories": sum(item["kind"] == "workspace" for item in entries),
            "environment_directories": sum(item["kind"] == "environment" for item in entries),
            "model_directories": sum(item["kind"] == "model" for item in entries),
        },
        "totals": totals,
        "entries": entries,
        "status": "planned",
    }


def plan(root: Path, destination: Path, min_workspace_mib: int = 100) -> Path:
    value = build_plan(root, destination, min_workspace_mib)
    target = root / PLAN_RELATIVE
    _write_json(target, value)
    return target


def _same_device(source: Path, destination_parent: Path) -> bool:
    return source.stat().st_dev == destination_parent.stat().st_dev


def _verify_entry(root: Path, archive_root: Path, item: dict[str, Any], *, source_expected: bool) -> None:
    source = root / item["source_relative"]
    target = archive_root / item["archive_relative"]
    if source_expected and not source.exists():
        raise RuntimeError(f"source unexpectedly absent: {source}")
    if not source_expected and source.exists():
        raise RuntimeError(f"archived source still active: {source}")
    if not target.exists():
        raise RuntimeError(f"archived item missing: {target}")
    actual = _inventory(target, hash_all=item.get("kind") == "model", allow_symlinks=item.get("kind") == "environment")
    for key in ("logical_bytes", "file_count", "directory_count", "root_device"):
        if actual[key] != item[key]:
            raise RuntimeError(f"{item['source_relative']} {key} mismatch")
    if actual["root_inode"] != item["root_inode"]:
        raise RuntimeError(f"{item['source_relative']} inode mismatch")
    if actual["selected_hashes"] != item.get("selected_hashes", {}):
        raise RuntimeError(f"{item['source_relative']} selected hash mismatch")
    if actual["symlinks"] != item.get("symlinks", {}):
        raise RuntimeError(f"{item['source_relative']} symlink mismatch")


def execute(root: Path, plan_path: Path) -> Path:
    specification = _read_json(plan_path)
    archive_root = Path(specification["destination"]).expanduser().absolute()
    source_root = Path(specification["source_root"]).expanduser().absolute()
    if source_root != root.absolute():
        raise RuntimeError("archive plan belongs to a different repository root")
    if archive_root.exists():
        journal_path = archive_root / "archive-journal.json"
        if not journal_path.exists():
            raise RuntimeError(f"destination already exists: {archive_root}")
        journal = _read_json(journal_path)
        if journal.get("plan_digest") != sha256(plan_path):
            raise RuntimeError("existing archive journal does not match this plan")
    else:
        parent = archive_root.parent
        parent.mkdir(parents=True, exist_ok=True)
        if not _same_device(root, parent):
            raise RuntimeError("archive destination is on a different filesystem")
        archive_root.mkdir()
        journal = {
            "archive_revision": specification["archive_revision"],
            "plan_digest": sha256(plan_path),
            "source_root": str(root.absolute()),
            "destination": str(archive_root),
            "entries": {item["source_relative"]: "planned" for item in specification["entries"]},
            "status": "in_progress",
        }
        _write_json(archive_root / "archive-journal.json", journal)
    journal_path = archive_root / "archive-journal.json"
    for item in specification["entries"]:
        source = root / item["source_relative"]
        target = archive_root / item["archive_relative"]
        state = journal["entries"].get(item["source_relative"], "planned")
        if state == "complete":
            _verify_entry(root, archive_root, item, source_expected=False)
            continue
        if not source.exists():
            raise RuntimeError(f"planned source missing: {source}")
        if target.exists():
            raise RuntimeError(f"archive collision: {target}")
        if not _same_device(source, archive_root.parent):
            raise RuntimeError(f"source is on a different filesystem: {source}")
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)
        _verify_entry(root, archive_root, item, source_expected=False)
        journal["entries"][item["source_relative"]] = "complete"
        _write_json(journal_path, journal)
    journal["status"] = "complete"
    _write_json(journal_path, journal)
    manifest = {
        "archive_revision": specification["archive_revision"],
        "source_root": specification["source_root"],
        "destination": str(archive_root),
        "plan_digest": journal["plan_digest"],
        "finalized": True,
        "entries": specification["entries"],
        "totals": specification["totals"],
    }
    _write_json(archive_root / "archive-manifest.json", manifest)
    (archive_root / "README.md").write_text(
        "# Pre-Prototype Research Artifact Archive\n\n"
        "Created by `python -m ltm archive-execute`. This is a reversible local "
        "archive of ignored historical artifacts; nothing was deleted. Restore "
        "an item explicitly with `python -m ltm archive-restore`.\n"
    )
    pointer = {
        "archive": str(archive_root),
        "manifest_sha256": sha256(archive_root / "archive-manifest.json"),
        "archive_revision": manifest["archive_revision"],
        "finalized": True,
    }
    _write_json(root / POINTER_RELATIVE, pointer)
    return archive_root / "archive-manifest.json"


def verify(root: Path, archive_root: Path) -> dict[str, Any]:
    archive_root = archive_root.expanduser().absolute()
    manifest_path = archive_root / "archive-manifest.json"
    journal_path = archive_root / "archive-journal.json"
    if not manifest_path.exists() or not journal_path.exists():
        raise RuntimeError("archive manifest and journal are required")
    manifest = _read_json(manifest_path)
    journal = _read_json(journal_path)
    if not manifest.get("finalized") or journal.get("status") != "complete":
        raise RuntimeError("archive is not finalized")
    if any(value != "complete" for value in journal.get("entries", {}).values()):
        raise RuntimeError("archive journal has incomplete entries")
    for item in manifest["entries"]:
        _verify_entry(root, archive_root, item, source_expected=False)
        if (root / item["source_relative"]).exists():
            raise RuntimeError(f"archived source still active: {item['source_relative']}")
    pointer = root / POINTER_RELATIVE
    if pointer.exists():
        value = _read_json(pointer)
        if value.get("manifest_sha256") != sha256(manifest_path):
            raise RuntimeError("repository archive pointer does not match manifest")
    return {
        "verified": True,
        "archive": str(archive_root),
        "manifest_sha256": sha256(manifest_path),
        "entries": len(manifest["entries"]),
        "totals": manifest["totals"],
    }


def restore(root: Path, archive_root: Path, item: str) -> Path:
    archive_root = archive_root.expanduser().absolute()
    manifest = _read_json(archive_root / "archive-manifest.json")
    selected = next((entry for entry in manifest["entries"] if entry["source_relative"] == item), None)
    if selected is None:
        raise RuntimeError(f"archive item not found: {item}")
    source = root / selected["source_relative"]
    target = archive_root / selected["archive_relative"]
    if source.exists():
        raise RuntimeError(f"restore target is occupied: {source}")
    if not target.exists():
        raise RuntimeError(f"archived item is missing: {target}")
    target.rename(source)
    actual = _inventory(source)
    if actual["logical_bytes"] != selected["logical_bytes"] or actual["selected_hashes"] != selected["selected_hashes"]:
        raise RuntimeError(f"restored item verification failed: {item}")
    log = archive_root / "restore-log.jsonl"
    with log.open("a") as handle:
        handle.write(json.dumps({"item": item, "restored_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, sort_keys=True) + "\n")
    return source


def status(root: Path) -> dict[str, Any]:
    pointer = root / POINTER_RELATIVE
    if not pointer.exists():
        return {"present": False, "pointer": str(POINTER_RELATIVE)}
    value = _read_json(pointer)
    archive_root = Path(value["archive"])
    try:
        verification = verify(root, archive_root)
    except (OSError, RuntimeError, json.JSONDecodeError) as error:
        return {"present": True, "verified": False, "error": str(error), "archive": str(archive_root)}
    return {"present": True, "verified": True, **verification}


def resolve_archived_path(path: Path | str, root: Path | None = None) -> Path:
    """Resolve an explicitly archived path without creating a symlink."""
    root = (root or Path.cwd()).absolute()
    path = Path(path)
    requested = path if path.is_absolute() else root / path
    if requested.exists():
        return requested
    try:
        relative = str(requested.relative_to(root))
    except ValueError:
        return requested
    pointer = root / POINTER_RELATIVE
    if not pointer.exists():
        return requested
    value = _read_json(pointer)
    archive_root = Path(value["archive"])
    manifest = _read_json(archive_root / "archive-manifest.json")
    for item in manifest.get("entries", []):
        source = item["source_relative"]
        if relative == source or relative.startswith(source + "/"):
            suffix = relative[len(source):].lstrip("/")
            target = archive_root / item["archive_relative"]
            return target / suffix if suffix else target
    return requested


def archived_catalog(root: Path) -> dict[str, Any]:
    info = status(root)
    if not info.get("verified"):
        return {"present": bool(info.get("present")), "verified": False, "error": info.get("error")}
    manifest = _read_json(Path(info["archive"]) / "archive-manifest.json")
    workspaces = [
        {key: item[key] for key in ("source_relative", "archive_relative", "logical_bytes", "file_count", "directory_count", "authoritative_for", "disposition")}
        for item in manifest["entries"] if item["kind"] == "workspace"
    ]
    return {"present": True, "verified": True, "count": len(workspaces), "workspaces": workspaces, "archive": info["archive"]}
