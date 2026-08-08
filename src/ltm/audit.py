"""Repository and foundation audit used before the first LTM build."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from .local_archive import POINTER_RELATIVE, archived_catalog
from .local_archive import status as archive_status

_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
_GAPS = {
    "g01": "topology_g1", "g02": "topology_g2", "g02-1": "topology_g21",
    "g02-2": "topology_g22", "g02-3": "topology_g23", "g02-4": "topology_g24",
    "g02-5": "topology_g25", "g02-6": "topology_g26", "g02-7": "topology_g27",
    "g02-8": "topology_g28", "g02-9": "topology_g29", "g02-10": "topology_g210",
    "g02-11": "topology_g211", "g02-12": "topology_g212", "g02-13": "topology_g213",
    "g02-14": "topology_g214",
    "g03": "topology_g3", "g04": "topology_g4", "g05": "topology_g5",
    "g06": "topology_g6", "g07": "topology_g7", "g08": "topology_g8",
    "g09": "topology_g9", "g10": "topology_g10", "g10-1": "topology_g101",
    "g11": "topology_g11", "g12": "topology_g12", "g13": "topology_g13",
    "g14": "topology_g14",
}
_REGISTRY = Path("docs/experiments/registry.json")
_SERIES_SUMMARY = Path("docs/experiments/series-summary.md")
_COMPONENT_INTERNALS = Path("docs/architecture/component-internals.md")
_MOTHER_ARCHITECTURE = Path("docs/architecture/mother-architecture.md")
_LOCK_MANIFEST = Path("docs/architecture/architecture-lock-v1.manifest.json")
_LOCK_FILES = (
    Path("docs/architecture/architecture-lock-v1.md"),
    Path("docs/architecture/mother-architecture.md"),
    _COMPONENT_INTERNALS,
    Path("configs/ltm-architecture-v1.json"),
    _REGISTRY,
    Path("src/topology_g1/registry.py"),
    Path("src/ltm_r2/schemas.py"),
    Path("src/ltm/schema.py"),
)
_REGISTRY_KEYS = {
    "experiment_id", "series", "title", "status", "classification",
    "authority_level", "package_path", "test_path", "config_path",
    "specification_path", "report_path", "authoritative_workspace",
    "predecessor", "successor", "adopted_component", "claim_boundary",
    "known_limitations",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _broken_links(root: Path) -> list[dict[str, str]]:
    broken: list[dict[str, str]] = []
    documents = [root / "README.md", *sorted((root / "docs").rglob("*.md"))]
    for document in documents:
        for target in _LINK.findall(document.read_text()):
            target = target.split("#", 1)[0].strip()
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            if not (document.parent / target).resolve().exists():
                broken.append({"document": str(document.relative_to(root)), "target": target})
    return broken


def _ignored(root: Path, path: str) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "-q", path], cwd=root, check=False,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def _registry_audit(root: Path) -> dict[str, object]:
    registry = json.loads((root / _REGISTRY).read_text())
    rows = registry["experiments"]
    ids = [row.get("experiment_id") for row in rows]
    duplicate_ids = sorted({item for item in ids if ids.count(item) > 1})
    allowed = set(registry["status_values"])
    invalid_statuses = sorted(
        f"{row.get('experiment_id')}:{row.get('status')}"
        for row in rows if row.get("status") not in allowed
    )
    missing_fields = sorted(
        f"{row.get('experiment_id')}:{key}"
        for row in rows for key in _REGISTRY_KEYS if key not in row
    )
    missing_paths = []
    for row in rows:
        for key in ("package_path", "test_path", "config_path", "specification_path", "report_path"):
            value = row.get(key)
            if value and not (root / value).exists():
                missing_paths.append(f"{row['experiment_id']}:{value}")
        workspace = row.get("authoritative_workspace")
        if workspace and not _ignored(root, workspace):
            missing_paths.append(f"{row['experiment_id']}:UNIGNORED:{workspace}")
    ledger = (root / "docs/roadmap/results-ledger.md").read_text()
    unledgered = sorted(
        row["experiment_id"] for row in rows
        if row["status"] != "PLANNED" and row["experiment_id"] not in ledger
    )
    summary = (root / _SERIES_SUMMARY).read_text() if (root / _SERIES_SUMMARY).exists() else ""
    summary_missing_ids = sorted(row["experiment_id"] for row in rows if row["experiment_id"] not in summary)
    by_id = {row["experiment_id"]: row for row in rows}
    chain_inconsistencies = []
    for row in rows:
        predecessor = row.get("predecessor")
        successor = row.get("successor")
        # Historical research forks are intentionally one-way (for example G2
        # feeds both G2.1 and G3). The L series is a declared linear lineage and
        # is therefore audited bidirectionally.
        if row["series"] == "L" and predecessor in by_id and by_id[predecessor].get("successor") != row["experiment_id"]:
            chain_inconsistencies.append(f"{row['experiment_id']}:predecessor:{predecessor}")
        if row["series"] == "L" and successor in by_id and by_id[successor].get("predecessor") != row["experiment_id"]:
            chain_inconsistencies.append(f"{row['experiment_id']}:successor:{successor}")
    component_text = (root / _COMPONENT_INTERNALS).read_text() if (root / _COMPONENT_INTERNALS).exists() else ""
    required_component_headings = (
        "## 1. The Compiler",
        "## 2. The Latent Dynamic Field",
        "## 3. The Latent Optimization",
        "## 4. The Decoder",
    )
    missing_component_headings = [
        heading for heading in required_component_headings if heading not in component_text
    ]
    mother_text = (root / _MOTHER_ARCHITECTURE).read_text() if (root / _MOTHER_ARCHITECTURE).exists() else ""
    missing_maturity_labels = [
        label for label in ("**Validated**", "**Provisional**", "**Planned**")
        if label not in mother_text or label not in component_text
    ]
    return {
        "count": len(rows),
        "duplicate_ids": duplicate_ids,
        "invalid_statuses": invalid_statuses,
        "missing_fields": missing_fields,
        "missing_paths": sorted(missing_paths),
        "unledgered": unledgered,
        "summary_missing_ids": summary_missing_ids,
        "chain_inconsistencies": sorted(chain_inconsistencies),
        "missing_component_headings": missing_component_headings,
        "missing_maturity_labels": missing_maturity_labels,
    }


def architecture_manifest(root: Path) -> dict[str, object]:
    return {
        "architecture_id": "LTM-ARCH-1.1",
        "evidence_cutoff": "2026-08-08",
        "files": {str(path): _sha256(root / path) for path in _LOCK_FILES},
    }


def write_architecture_manifest(root: Path) -> dict[str, object]:
    value = architecture_manifest(root)
    (root / _LOCK_MANIFEST).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    return value


def _lock_mismatches(root: Path) -> list[str]:
    path = root / _LOCK_MANIFEST
    if not path.exists():
        return [str(_LOCK_MANIFEST)]
    expected = json.loads(path.read_text())
    actual = architecture_manifest(root)
    mismatches = [
        name for name, digest in actual["files"].items()
        if expected.get("files", {}).get(name) != digest
    ]
    if expected.get("architecture_id") != actual["architecture_id"]:
        mismatches.append("architecture_id")
    if expected.get("evidence_cutoff") != actual["evidence_cutoff"]:
        mismatches.append("evidence_cutoff")
    if set(expected.get("files", {})) != set(actual["files"]):
        mismatches.append("manifest_file_set")
    return sorted(mismatches)


def _directory_size(path: Path) -> int:
    total = 0
    for directory, _children, files in os.walk(path):
        for name in files:
            try:
                total += (Path(directory) / name).stat().st_size
            except FileNotFoundError:
                pass
    return total


def _workspace_catalog(root: Path) -> dict[str, object]:
    registry = json.loads((root / _REGISTRY).read_text())["experiments"]
    authorities = {
        row["authoritative_workspace"]: row["experiment_id"]
        for row in registry if row.get("authoritative_workspace")
    }
    rows = []
    for path in sorted((root / "workspaces").iterdir()):
        if not path.is_dir() or path.name == "_repository-catalog":
            continue
        relative = str(path.relative_to(root))
        artifacts = {}
        for name in ("frozen-manifest.json", "locked-results.json", "report.json", "verification.json", "selected-kernel.pt"):
            artifact = path / name
            if artifact.exists():
                artifacts[name] = {
                    "bytes": artifact.stat().st_size,
                    "sha256": _sha256(artifact)
                    if artifact.stat().st_size <= 10_000_000
                    or (relative == "workspaces/ltm-inference-i3-1-r13" and name == "selected-kernel.pt")
                    else None,
                }
        rows.append({
            "workspace": relative,
            "bytes": _directory_size(path),
            "authoritative_for": authorities.get(relative),
            "disposition": "authoritative" if relative in authorities else "preserved-unclassified",
            "artifacts": artifacts,
        })
    return {"preservation_policy": "catalog-and-preserve", "count": len(rows), "workspaces": rows}


def _environment_catalog(root: Path) -> dict[str, object]:
    rows = []
    for name, role in ((".venv", "canonical-python-3.11"), (".venv-g101", "historical-unsupported")):
        executable = root / name / "bin/python"
        if not executable.exists():
            rows.append({"path": name, "role": role, "present": False})
            continue
        version = subprocess.run([str(executable), "-V"], capture_output=True, text=True, check=False)
        check = subprocess.run([str(executable), "-m", "pip", "check"], capture_output=True, text=True, check=False)
        package_result = subprocess.run(
            [str(executable), "-m", "pip", "list", "--format=json"],
            capture_output=True,
            text=True,
            check=False,
        )
        rows.append({
            "path": name,
            "role": role,
            "present": True,
            "version": (version.stdout or version.stderr).strip(),
            "pip_check": check.returncode,
            "pip_check_output": (check.stdout + check.stderr).strip(),
            "packages": json.loads(package_result.stdout) if package_result.returncode == 0 else [],
            "ignored": _ignored(root, name),
        })
    archive = archive_status(root)
    if archive.get("verified"):
        manifest = json.loads((Path(archive["archive"]) / "archive-manifest.json").read_text())
        if any(item["source_relative"] == ".venv-g101" for item in manifest["entries"]):
            rows.append({"path": ".venv-g101", "role": "historical-unsupported", "present": False, "archived": True})
    return {"running_python": sys.version.split()[0], "environments": rows}


def _model_catalog(root: Path) -> dict[str, object]:
    models = []
    model_root = root / ".models"
    if model_root.exists():
        for path in sorted(model_root.iterdir()):
            if path.is_dir():
                models.append({"name": path.name, "bytes": _directory_size(path), "ignored": _ignored(root, str(path.relative_to(root)))})
    manifest = model_root / "model-manifest.json"
    allowlisted = set()
    if manifest.exists():
        try:
            value = json.loads(manifest.read_text())
            records = value.get("models", value.get("entries", []))
            records = records.values() if isinstance(records, dict) else records
            for record in records:
                if isinstance(record, str):
                    allowlisted.add(Path(record).name)
                elif isinstance(record, dict):
                    for key in ("path", "relative_path", "name", "directory"):
                        if record.get(key):
                            allowlisted.add(Path(str(record[key])).name)
                            break
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "count": len(models),
        "models": models,
        "manifest_present": manifest.exists(),
        "unmanifested_models": sorted(item["name"] for item in models if item["name"] not in allowlisted),
    }


def _archive_audit(root: Path) -> dict[str, object]:
    info = archive_status(root)
    failures: list[str] = []
    if info.get("present") and not info.get("verified"):
        failures.append("ARCHIVE_UNVERIFIED")
    if info.get("verified"):
        manifest = json.loads((Path(info["archive"]) / "archive-manifest.json").read_text())
        archived_sources = {entry["source_relative"] for entry in manifest["entries"]}
        if (root / ".venv-g101").exists() and ".venv-g101" in archived_sources:
            failures.append("HISTORICAL_ENVIRONMENT_STILL_ACTIVE")
        models = _model_catalog(root)
        if models["unmanifested_models"]:
            failures.append("UNMANIFESTED_MODEL_ACTIVE")
        for required in (".venv", ".models/model-manifest.json", ".models/all-MiniLM-L6-v2", ".models/flan-t5-small"):
            if not (root / required).exists():
                failures.append(f"RETAINED_ASSET_MISSING:{required}")
        registry = json.loads((root / _REGISTRY).read_text())["experiments"]
        available = {entry["source_relative"] for entry in manifest["entries"]}
        for row in registry:
            workspace = row.get("authoritative_workspace")
            if workspace and not (root / workspace).exists() and workspace not in available:
                failures.append(f"AUTHORITATIVE_WORKSPACE_MISSING:{workspace}")
        journal = Path(info["archive"]) / "archive-journal.json"
        if not journal.exists() or json.loads(journal.read_text()).get("status") != "complete":
            failures.append("ARCHIVE_JOURNAL_DISAGREEMENT")
    return {"status": info, "failures": sorted(set(failures))}


def audit_repository(root: Path) -> dict[str, object]:
    missing: list[str] = []
    for gap, package in _GAPS.items():
        config_id = "-".join([str(int(part)) for part in gap[1:].split("-")])
        for path in (
            root / "src" / package,
            root / "tests" / package,
            root / "configs" / f"topology-g{config_id}.json",
            root / "docs" / "experiments" / "gaps" / gap / "specification.md",
            root / "docs" / "experiments" / "gaps" / gap / "report.md",
        ):
            if not path.exists():
                missing.append(str(path.relative_to(root)))
    reports = {
        str(path.relative_to(root)): _sha256(path)
        for path in sorted((root / "docs" / "experiments").rglob("report.md"))
    }
    tracked_generated = []
    tracked_large_files = []
    tracked = subprocess.run(["git", "ls-files"], cwd=root, check=True, capture_output=True, text=True).stdout.splitlines()
    for path in tracked:
        if path.startswith(("workspaces/", ".models/", ".venv/", ".venv-")) or path.endswith((".pt", ".safetensors", ".npz")):
            tracked_generated.append(path)
        file_path = root / path
        if file_path.exists() and file_path.stat().st_size > 5_000_000:
            tracked_large_files.append(path)
    registry = _registry_audit(root)
    environments = _environment_catalog(root)
    canonical = next((item for item in environments["environments"] if item["path"] == ".venv"), {})
    archive = _archive_audit(root)
    return {
        "repository_root": str(root),
        "gap_contract_missing": sorted(missing),
        "broken_markdown_links": _broken_links(root),
        "report_hashes": reports,
        "ignored_assets": {
            path: _ignored(root, path) for path in (".models", ".venv", ".venv-g101", "workspaces")
        },
        "tracked_generated": tracked_generated,
        "tracked_large_files": tracked_large_files,
        "experiment_registry": registry,
        "architecture_lock_mismatches": _lock_mismatches(root),
        "canonical_environment": canonical,
        "archive": archive,
        "archive_pointer": str(root / POINTER_RELATIVE) if (root / POINTER_RELATIVE).exists() else None,
        "model_catalog": _model_catalog(root),
        "source_packages": len([item for item in (root / "src").iterdir() if item.is_dir()]),
        "test_packages": len([item for item in (root / "tests").iterdir() if item.is_dir()]),
        "config_files": len(list((root / "configs").glob("*.json"))),
        "registered_paths": {
            "source_packages": len({row["package_path"] for row in json.loads((root / _REGISTRY).read_text())["experiments"] if row.get("package_path")}),
            "test_packages": len({row["test_path"] for row in json.loads((root / _REGISTRY).read_text())["experiments"] if row.get("test_path")}),
            "config_files": len({row["config_path"] for row in json.loads((root / _REGISTRY).read_text())["experiments"] if row.get("config_path")}),
        },
    }


def write_audit(root: Path, workspace: Path) -> dict[str, object]:
    result = audit_repository(root)
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "experiment-audit.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    (workspace / "workspace-catalog.json").write_text(json.dumps(_workspace_catalog(root), indent=2, sort_keys=True) + "\n")
    (workspace / "active-workspace-catalog.json").write_text(json.dumps(_workspace_catalog(root), indent=2, sort_keys=True) + "\n")
    (workspace / "archived-workspace-catalog.json").write_text(json.dumps(archived_catalog(root), indent=2, sort_keys=True) + "\n")
    environments = _environment_catalog(root)
    (workspace / "environment-catalog.json").write_text(json.dumps(environments, indent=2, sort_keys=True) + "\n")
    (workspace / "model-catalog.json").write_text(json.dumps(_model_catalog(root), indent=2, sort_keys=True) + "\n")
    pointer = root / POINTER_RELATIVE
    if pointer.exists():
        (workspace / "archive-pointer.json").write_text(pointer.read_text())
        plan_path = workspace / "archive-plan.json"
        if not plan_path.exists() and (root / "workspaces/_repository-catalog/archive-plan.json").exists():
            plan_path.write_text((root / "workspaces/_repository-catalog/archive-plan.json").read_text())
    readiness = {
        "architecture_id": "LTM-ARCH-1.1",
        "ready": not any((result["gap_contract_missing"], result["broken_markdown_links"], result["tracked_generated"], result["tracked_large_files"], result["architecture_lock_mismatches"], result["archive"]["failures"], result["experiment_registry"]["duplicate_ids"], result["experiment_registry"]["invalid_statuses"], result["experiment_registry"]["missing_fields"], result["experiment_registry"]["missing_paths"], result["experiment_registry"]["unledgered"], result["experiment_registry"]["summary_missing_ids"], result["experiment_registry"]["chain_inconsistencies"], result["experiment_registry"]["missing_component_headings"], result["experiment_registry"]["missing_maturity_labels"], result["canonical_environment"].get("pip_check") != 0)),
        "archive": result["archive"],
        "commit_created": False,
        "push_performed": False,
    }
    (workspace / "push-readiness.json").write_text(json.dumps(readiness, indent=2, sort_keys=True) + "\n")
    return result


def assert_clean(result: dict[str, object]) -> None:
    failures = []
    if result["gap_contract_missing"]:
        failures.append("GAP_CONTRACT_MISSING")
    if result["broken_markdown_links"]:
        failures.append("BROKEN_MARKDOWN_LINK")
    if result["tracked_generated"]:
        failures.append("TRACKED_GENERATED_ARTIFACT")
    if result["tracked_large_files"]:
        failures.append("UNEXPECTED_LARGE_TRACKED_FILE")
    registry = result["experiment_registry"]
    if any(registry[key] for key in (
        "duplicate_ids", "invalid_statuses", "missing_fields", "missing_paths",
        "unledgered", "summary_missing_ids", "chain_inconsistencies",
        "missing_component_headings", "missing_maturity_labels",
    )):
        failures.append("EXPERIMENT_REGISTRY_INVALID")
    if result["architecture_lock_mismatches"]:
        failures.append("ARCHITECTURE_LOCK_MISMATCH")
    failures.extend(result["archive"]["failures"])
    environment = result["canonical_environment"]
    if not environment.get("version", "").startswith("Python 3.11") or environment.get("pip_check") != 0:
        failures.append("CANONICAL_ENVIRONMENT_INVALID")
    if any(not ignored and (Path(result["repository_root"]) / path).exists() for path, ignored in result["ignored_assets"].items()):
        failures.append("UNIGNORED_LOCAL_ASSET")
    if failures:
        raise RuntimeError(",".join(failures))
