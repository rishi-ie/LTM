"""Public Parasite runtime orchestrating the four replaceable components."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from parasite.compiler import compile_ingest
from parasite.contracts import CompileResult, IngestRequest, QueryRequest, RuntimeResult
from parasite.decoder import decode
from parasite.field import FieldStore
from parasite.integrity import digest
from parasite.optimizer import execute_exact, solve_equilibrium, verify_equilibrium


class ParasiteRuntime:
    def __init__(self, state_path: Path, config_path: Path):
        self.state_path = state_path
        self.config_path = config_path
        self.config = json.loads(config_path.read_text(encoding="utf-8"))
        if self.config.get("runtime_revision") != "parasite-runtime/0.1":
            raise ValueError("UNSUPPORTED_RUNTIME_REVISION")
        self.repository_root = config_path.resolve().parents[2]
        self.field = FieldStore(state_path)
        self.renderer = None
        if self.config.get("decoder", {}).get("use_flan_candidate_scorer", False):
            from parasite.decoder.flan import renderer

            self.renderer = renderer(self.repository_root / self.config["decoder"]["model_path"])

    @classmethod
    def open(cls, state_path: str | Path, config_path: str | Path) -> ParasiteRuntime:
        return cls(Path(state_path).resolve(), Path(config_path).resolve())

    def close(self) -> None:
        self.field.close()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()

    @property
    def revisions(self) -> tuple[tuple[str, str], ...]:
        return tuple((key, self.config[key]) for key in (
            "compiler_revision", "field_revision", "optimizer_revision", "decoder_revision", "integrity_revision",
        ))

    def ingest(self, request: IngestRequest) -> CompileResult:
        result, candidate = compile_ingest(request, self.repository_root)
        if candidate is None or result.disposition != "accept":
            return result
        try:
            if request.input_kind == "conversation_turn":
                if request.session_id is None:
                    return replace(result, disposition="quarantine", failure_codes=("SESSION_ID_REQUIRED",))
                receipt = self.field.commit_session_event(candidate, request.session_id)
            else:
                receipt = self.field.commit(candidate)
        except (OSError, RuntimeError, ValueError) as exc:
            return replace(result, disposition="quarantine", failure_codes=(str(exc),))
        evidence = dict(result.evidence)
        evidence.update({"generation_id": receipt.generation_id, "committed": receipt.committed})
        if candidate.nodes:
            evidence["object_ids"] = tuple(item.node_id for item in candidate.nodes)
        return CompileResult("accept", result.transaction_id, receipt.substrate_hash, receipt.fieldir_hash, (), tuple(sorted(evidence.items())))

    @staticmethod
    def _resolve_atom(loaded, value: str) -> str:
        exact = {atom.atom_id for atom in loaded.atoms}
        if value in exact:
            return value
        matching = [atom.atom_id for atom in loaded.atoms if atom.expression == value]
        if len(matching) != 1:
            raise ValueError("ATOM_REFERENCE_NOT_UNIQUE")
        return matching[0]

    def ask(self, request: QueryRequest) -> RuntimeResult:
        style = self._response_style(request)
        base_trace: tuple[tuple[str, Any], ...] = self.revisions + (
            ("tenant_id", request.tenant_id), ("reality_id", request.reality_id), ("profile_id", request.profile_id),
        )
        if request.profile_id == "conversation_memory":
            if request.session_id is None:
                return decode(disposition="clarification_required", failures=("SESSION_ID_REQUIRED",), trace=base_trace)
            rows = self.field.session_rows(request.tenant_id, request.reality_id, request.session_id)
            preferences = tuple(f"{row.get('preference_key')}={row.get('preference_value')}" for row in rows if row.get("action") == "set_preference")
            reported = tuple(str(row.get("content")) for row in rows if row.get("object_kind") == "claim" or row.get("action") in {"none", "correct"})
            text = f"Preferences: {', '.join(preferences) or 'none'}. User-reported context: {', '.join(reported) or 'none'}."
            result = RuntimeResult("candidate", (), preferences + reported, (), (), 0.0, (), text, base_trace + (("assistant_evidence_authority", 0.25),), ())
        else:
            loaded = self.field.load(request.tenant_id, request.reality_id)
            if loaded is None:
                return decode(disposition="unknown", failures=("REALITY_EMPTY",), trace=base_trace)
            if request.profile_id == "exact":
                target = str(request.payload.get("target_atom_id", ""))
                try:
                    target = self._resolve_topology_target(loaded, target)
                    exact = execute_exact(loaded, query_id=request.query_id, target_atom_id=target, scope_key=request.scope_key, session_id=request.session_id, valid_at=request.valid_at)
                except (KeyError, RuntimeError, ValueError) as exc:
                    return decode(disposition="verification_failed", failures=(str(exc),), trace=base_trace)
                labels = tuple(self._label(loaded, item) for item in exact.authorized_claims)
                result = decode(
                    disposition=exact.disposition if exact.verified else "verification_failed", claims=labels,
                    certificate=exact.proof_ids, verified=exact.verified, tension=exact.uncertainty,
                    trace=base_trace + (("coverage", "complete_partition"), ("g6_rounds", "bounded"), ("g7", "executed"), ("g9", "independent_replay")),
                    failures=exact.failure_codes, style=style,
                    renderer=self.renderer,
                )
            else:
                try:
                    assumptions = tuple(self._resolve_atom(loaded, str(item)) for item in request.payload["assumptions"])
                    query_expression = str(request.payload["query_expression"])
                    query_sort = str(request.payload["query_sort"])
                    limits = self.config["equilibrium"]
                    if len(loaded.factors) > int(limits["maximum_factors"]):
                        return decode(disposition="incomplete_coverage", failures=("FACTOR_LIMIT_EXCEEDED",), trace=base_trace)
                    equilibrium = solve_equilibrium(
                        loaded.atoms, loaded.factors, assumption_atom_ids=assumptions,
                        query_expression=query_expression, query_sort=query_sort, scope_key=request.scope_key,
                        valid_at=request.valid_at, maximum_sweeps=int(limits["maximum_sweeps"]),
                        confidence_threshold=float(limits["candidate_threshold"]), alternative_margin=float(limits["alternative_margin"]),
                    )
                    verification = verify_equilibrium(
                        loaded.atoms, loaded.factors, equilibrium, assumptions=assumptions, query_expression=query_expression,
                        query_sort=query_sort, scope_key=request.scope_key, valid_at=request.valid_at,
                    )
                except (KeyError, RuntimeError, ValueError) as exc:
                    return decode(disposition="verification_failed", failures=(str(exc),), trace=base_trace)
                if not verification.verified:
                    result = decode(disposition="verification_failed", failures=(verification.failure_code or "VERIFY_FAILED",), trace=base_trace)
                else:
                    selected = next((item for item in equilibrium.candidates if item.candidate_id == equilibrium.selected_candidate_id), None)
                    claims = () if selected is None else (("not " if selected.polarity < 0 else "") + selected.expression,)
                    alternatives = tuple(("not " if item.polarity < 0 else "") + item.expression for item in equilibrium.candidates) if equilibrium.disposition == "alternatives" else ()
                    tension = 0.0 if selected is None else selected.opposing_activation
                    result = decode(
                        disposition=equilibrium.disposition, claims=claims, alternatives=alternatives,
                        support=verification.supporting_sources, opposition=verification.opposing_sources, tension=tension,
                        certificate=verification.certificate, verified=True, style=style,
                        trace=base_trace + (("sweeps", len(equilibrium.trajectory)), ("objective", equilibrium.objective), ("residual", equilibrium.residual), ("independent_fixed_point", True)),
                        renderer=self.renderer,
                    )
        if request.session_id is not None:
            self.field.store_assistant_response(request.tenant_id, request.reality_id, request.session_id, result.response_text, request.query_id)
        return result

    def _response_style(self, request: QueryRequest) -> str:
        if request.session_id is None:
            return request.requested_style
        rows = self.field.session_rows(request.tenant_id, request.reality_id, request.session_id)
        for row in reversed(rows):
            if row.get("action") == "set_preference" and row.get("preference_key") in {"style", "response_style"} and row.get("preference_value") in {"brief", "detailed"}:
                return str(row["preference_value"])
        return request.requested_style

    @staticmethod
    def _resolve_topology_target(loaded, value: str) -> str:
        if value in {node.node_id for node in loaded.nodes}:
            return value
        matching = [node.node_id for node in loaded.nodes if str(node.attr("public_id", "")) == value]
        if len(matching) != 1:
            raise ValueError("TARGET_REFERENCE_NOT_UNIQUE")
        return matching[0]

    @staticmethod
    def _label(loaded, atom_id: str) -> str:
        node = next(node for node in loaded.nodes if node.node_id == atom_id)
        return str(node.attr("expression", node.attr("content", node.attr("public_id", atom_id))))

    def delete(self, tenant_id: str, reality_id: str, object_id: str) -> bool:
        return self.field.delete_session_object(tenant_id, reality_id, object_id) or self.field.delete_base(tenant_id, reality_id, object_id)

    def clear_session(self, tenant_id: str, session_id: str) -> int:
        return self.field.clear_session(tenant_id, session_id)

    def inspect(self, tenant_id: str, reality_id: str) -> dict:
        return self.field.inspect(tenant_id, reality_id)

    def verify(self, tenant_id: str, reality_id: str) -> dict:
        loaded = self.field.load(tenant_id, reality_id)
        return {
            "tenant_id": tenant_id, "reality_id": reality_id, "verified": loaded is not None,
            "generation_id": None if loaded is None else loaded.generation_id,
            "generation_hash": None if loaded is None else digest(loaded.manifest),
            "revisions": dict(self.revisions),
        }
