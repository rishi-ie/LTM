from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


def _bootstrap(root: Path) -> None:
    parasite_src = root.parent / "Parasite" / "src"
    project_src = root.parent / "src"
    for item in (parasite_src, project_src):
        if str(item) not in sys.path:
            sys.path.insert(0, str(item))


class L8Runtime:
    """L8 owns policy and optimizer state; Parasite is a read-only dependency."""

    def __init__(self, state_path: Path, config_path: Path, baseline_root: Path):
        _bootstrap(Path(__file__).resolve().parents[2])
        self.state_path = state_path
        self.config_path = config_path
        self.baseline_root = baseline_root
        self.state_path.mkdir(parents=True, exist_ok=True)
        (self.state_path / "policies").mkdir(exist_ok=True)
        self.config = json.loads(config_path.read_text(encoding="utf-8"))
        self.baseline_manifest = self._hash_baseline()
        self._write_once(self.state_path / "baseline-manifest.json", self.baseline_manifest)
        from parasite.field.store import FieldStore
        self.store = FieldStore(self.state_path / "field")

    @classmethod
    def open(cls, state_path: str | Path, config_path: str | Path | None = None) -> L8Runtime:
        root = Path(__file__).resolve().parents[2]
        return cls(Path(state_path), Path(config_path or root / "config/runtime-l8.json"), root.parent / "Parasite")

    def _hash_baseline(self) -> dict[str, Any]:
        paths = [self.baseline_root / "config/runtime-v1.json"]
        paths += sorted((self.baseline_root / "src/parasite").rglob("*.py"))
        return {"revision": "parasite-v0.1-read-only", "files": {str(item.relative_to(self.baseline_root)): hashlib.sha256(item.read_bytes()).hexdigest() for item in paths if item.exists()}}

    @staticmethod
    def _write_once(path: Path, value: Any) -> None:
        payload = json.dumps(value, sort_keys=True, indent=2) + "\n"
        if path.exists() and path.read_text(encoding="utf-8") != payload:
            raise ValueError("IMMUTABLE_ARTIFACT_COLLISION")
        if not path.exists():
            path.write_text(payload, encoding="utf-8")

    def ingest(self, request: Any) -> Any:
        from parasite.compiler.compile import compile_ingest
        result, candidate = compile_ingest(request, self.baseline_root.parent)
        if candidate is None or result.disposition != "accept":
            return result
        receipt = self.store.commit(candidate)
        classes = json.loads((self.state_path / "source-classes.json").read_text(encoding="utf-8")) if (self.state_path / "source-classes.json").exists() else {}
        classes.update({str(key): str(value) for key, value in request.payload.get("source_class_map", {}).items()})
        classes.setdefault(candidate.source_id, str(request.payload.get("source_class", candidate.source_id)))
        (self.state_path / "source-classes.json").write_text(json.dumps(classes, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        return receipt

    def compile_policy(self, policy_id: str, rows: list[dict[str, Any]]) -> Any:
        from .policy import compile_policy
        policy = compile_policy(policy_id, rows)
        self._write_once(self.state_path / "policies" / f"{policy_id}.json", {"policy_id": policy.policy_id, "revision": policy.revision, "hash": policy.hash, "instructions": [{"opcode": x.opcode, "value": x.value, "scope": x.scope, "priority": x.priority, "source_id": x.source_id} for x in policy.instructions]})
        return policy

    def ask(self, request: Any, policy_id: str = "default") -> Any:
        from .contracts import CompiledPolicy, PolicyInstruction
        from .evaluator import verify_result
        from .optimizer import solve_policy_equilibrium
        loaded = self.store.load(request.tenant_id, request.reality_id)
        if loaded is None:
            raise ValueError("REALITY_NOT_FOUND")
        path = self.state_path / "policies" / f"{policy_id}.json"
        if path.exists():
            raw = json.loads(path.read_text(encoding="utf-8"))
            policy = CompiledPolicy(raw["policy_id"], raw["revision"], tuple(PolicyInstruction(**item) for item in raw["instructions"]), raw["hash"])
        else:
            policy = self.compile_policy(policy_id, [])
        by_expression = {(atom.expression, atom.sort): atom.atom_id for atom in loaded.atoms}
        assumptions = tuple(by_expression[(str(item["expression"]), str(item["sort"]))] for item in request.payload.get("assumptions", ()))
        source_classes = json.loads((self.state_path / "source-classes.json").read_text(encoding="utf-8")) if (self.state_path / "source-classes.json").exists() else {}
        result = solve_policy_equilibrium(loaded.atoms, loaded.factors, assumptions=assumptions, query_expression=str(request.payload["query_expression"]), query_sort=str(request.payload["query_sort"]), policy=policy, source_classes=source_classes, scope=request.scope_key, valid_at=request.valid_at, maximum_sweeps=int(self.config["max_sweeps"]))
        verification = verify_result(result, loaded.atoms, loaded.factors, assumptions, str(request.payload["query_expression"]), str(request.payload["query_sort"]), policy, source_classes, request.scope_key, request.valid_at)
        if not verification["verified"]:
            return result
        return result
