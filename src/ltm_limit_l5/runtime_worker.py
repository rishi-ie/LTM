"""Process-isolated locked runtime with evaluator-path denial."""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import tempfile
from pathlib import Path


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, sort_keys=True, indent=2, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            raise RuntimeError(f"immutable artifact already exists: {path.name}")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class _RuntimeGuard:
    def __init__(self, roots: tuple[Path, ...]) -> None:
        self.roots = tuple(path.resolve() for path in roots)
        self.probe = False
        self.probe_denials = 0
        self.unexpected_denials = 0
        self.network_probe = False
        self.network_probe_denials = 0
        self.unexpected_network_attempts = 0

    def __call__(self, event: str, arguments: tuple[object, ...]) -> None:
        if event in {
            "socket.connect",
            "socket.connect_ex",
            "socket.getaddrinfo",
            "socket.gethostbyaddr",
            "socket.gethostbyname",
        }:
            if self.network_probe:
                self.network_probe_denials += 1
            else:
                self.unexpected_network_attempts += 1
            raise PermissionError("runtime network access denied")
        if event != "open" or not arguments:
            return
        raw = arguments[0]
        if not isinstance(raw, (str, bytes)):
            return
        candidate = Path(raw.decode() if isinstance(raw, bytes) else raw).resolve()
        if any(candidate == root or root in candidate.parents for root in self.roots):
            if self.probe:
                self.probe_denials += 1
            else:
                self.unexpected_denials += 1
            raise PermissionError(f"runtime evaluator-gold access denied: {candidate}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--limits-json", required=True)
    parser.add_argument("--forbid", action="append", type=Path, default=[])
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    audit_path = args.workspace / "locked-runtime-access-audit.json"
    guard = _RuntimeGuard(tuple(args.forbid))
    sys.addaudithook(guard)
    try:
        guard.probe = True
        for root in guard.roots:
            try:
                (root / "gold.jsonl").open("rb")
            except PermissionError:
                pass
        guard.probe = False
        guard.network_probe = True
        try:
            with socket.socket() as probe_socket:
                probe_socket.connect(("127.0.0.1", 9))
        except PermissionError:
            pass
        guard.network_probe = False
        lifecycle_import_guarded = "ltm_limit_l5.lifecycle" not in sys.modules
        from .lifecycle import L5Lifecycle

        lifecycle = L5Lifecycle(
            args.workspace,
            args.config,
            limits=json.loads(args.limits_json),
        )
        lifecycle._verify_freeze()
        lifecycle._run_compiler_locked(resume=args.resume)
        lifecycle._run_end_to_end_locked(resume=args.resume)
        lifecycle._run_public_locked(resume=args.resume)
        passed = (
            guard.probe_denials == len(guard.roots)
            and guard.unexpected_denials == 0
            and guard.network_probe_denials >= 1
            and guard.unexpected_network_attempts == 0
            and lifecycle_import_guarded
        )
        _write_json(
            audit_path,
            {
                "passed": passed,
                "guard_revision": "l5-runtime-gold-guard/1",
                "runtime_process_id": os.getpid(),
                "lifecycle_import_guarded": lifecycle_import_guarded,
                "gold_paths_probed": len(guard.roots),
                "probe_denials": guard.probe_denials,
                "runtime_gold_reads": 0,
                "unexpected_gold_access_denials": guard.unexpected_denials,
                "network_probe_denials": guard.network_probe_denials,
                "network_calls": guard.unexpected_network_attempts,
                "failure_codes": [] if passed else ["RUNTIME_GOLD_GUARD_FAILED"],
            },
        )
        return 0 if passed else 1
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        if not audit_path.exists():
            _write_json(
                audit_path,
                {
                    "passed": False,
                    "guard_revision": "l5-runtime-gold-guard/1",
                    "runtime_process_id": os.getpid(),
                    "lifecycle_import_guarded": (
                        "ltm_limit_l5.lifecycle" not in sys.modules
                    ),
                    "gold_paths_probed": len(guard.roots),
                    "probe_denials": guard.probe_denials,
                    "runtime_gold_reads": 0,
                    "unexpected_gold_access_denials": guard.unexpected_denials,
                    "network_probe_denials": guard.network_probe_denials,
                    "network_calls": guard.unexpected_network_attempts,
                    "failure_codes": ["LOCKED_RUNTIME_FAILED"],
                    "error": str(error),
                },
            )
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
