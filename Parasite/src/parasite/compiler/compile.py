"""Narrow, fail-closed compilers into one candidate transaction."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from topology_g1.registry import validate_relation
from topology_g1.schemas import (
    NodeKind,
    Provenance,
    RelationInstance,
    RoleBinding,
    TopologyNode,
    ValidityInterval,
)

from parasite.contracts import (
    CandidateTransaction,
    CompileResult,
    EquilibriumAtom,
    EquilibriumFactor,
    IngestRequest,
    stable_id,
)
from parasite.integrity import canonical_json, digest


def _source_text(request: IngestRequest) -> str:
    supplied = request.payload.get("source_text")
    if supplied is not None:
        if not isinstance(supplied, str) or not supplied:
            raise ValueError("INVALID_SOURCE_TEXT")
        return supplied
    return canonical_json({key: value for key, value in request.payload.items() if key != "source_text"})


def _result(disposition: str, transaction_id: str, failures: tuple[str, ...] = (), **evidence: Any) -> CompileResult:
    return CompileResult(disposition, transaction_id, None, None, failures, tuple(sorted(evidence.items())))


def _provenance(request: IngestRequest, source_text: str) -> tuple[Provenance, ...]:
    return (Provenance(request.source_id, 0, len(source_text), request.source_hash),)


def _node_id(request: IngestRequest, public_id: str) -> str:
    return stable_id("parasite-node-v1", request.tenant_id, request.reality_id, public_id)


def _relation_id(request: IngestRequest, public_id: str) -> str:
    return stable_id("parasite-relation-v1", request.tenant_id, request.reality_id, public_id)


def _attrs(value: dict[str, Any]) -> tuple[tuple[str, Any], ...]:
    allowed = (str, int, float, bool, type(None))
    if any(not isinstance(item, allowed) for item in value.values()):
        raise ValueError("NONSCALAR_ATTRIBUTE")
    return tuple(sorted(value.items()))


def _topology(request: IngestRequest, source_text: str, transaction_id: str) -> CandidateTransaction:
    raw_nodes = request.payload.get("nodes")
    raw_relations = request.payload.get("relations", ())
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise ValueError("TOPOLOGY_NODES_REQUIRED")
    provenance = _provenance(request, source_text)
    validity = ValidityInterval(request.valid_from, request.valid_to)
    identities: dict[str, str] = {}
    nodes = []
    for row in raw_nodes:
        public_id = str(row["id"])
        if public_id in identities:
            raise ValueError("DUPLICATE_PUBLIC_NODE_ID")
        identities[public_id] = _node_id(request, public_id)
        attributes = dict(row.get("attributes", {}))
        attributes.setdefault("public_id", public_id)
        nodes.append(TopologyNode(identities[public_id], 2, NodeKind(row["kind"]), _attrs(attributes), request.scope_key, validity, provenance))
    node_map = {item.node_id: item for item in nodes}
    relations = []
    for row in raw_relations:
        arguments = tuple(RoleBinding(str(item["role"]), identities[str(item["node_id"])]) for item in row["arguments"])
        relation = RelationInstance(
            _relation_id(request, str(row["id"])), 2, str(row["relation_type"]), arguments,
            request.scope_key, validity, float(row.get("confidence", 1.0)), float(row.get("authority", 1.0)), provenance,
        )
        validate_relation(relation, node_map)
        relations.append(relation)
    return CandidateTransaction(transaction_id, request.tenant_id, request.reality_id, request.source_id, source_text, tuple(nodes), tuple(relations))


def _math(request: IngestRequest, source_text: str, transaction_id: str) -> CandidateTransaction:
    raw_atoms = request.payload.get("atoms")
    raw_factors = request.payload.get("factors")
    if not isinstance(raw_atoms, list) or not raw_atoms or not isinstance(raw_factors, list) or not raw_factors:
        raise ValueError("MATHEMATICAL_ATOMS_AND_FACTORS_REQUIRED")
    provenance = _provenance(request, source_text)
    validity = ValidityInterval(request.valid_from, request.valid_to)
    public_to_exact: dict[str, str] = {}
    atoms: list[EquilibriumAtom] = []
    nodes: list[TopologyNode] = []
    for row in raw_atoms:
        public_id = str(row["id"])
        if public_id in public_to_exact:
            raise ValueError("DUPLICATE_MATHEMATICAL_ATOM")
        exact_id = _node_id(request, public_id)
        public_to_exact[public_id] = exact_id
        expression, sort = str(row["expression"]), str(row["sort"])
        atoms.append(EquilibriumAtom(exact_id, expression, sort, request.reality_id))
        nodes.append(TopologyNode(exact_id, 2, NodeKind.CLAIM, _attrs({"expression": expression, "public_id": public_id, "sort": sort}), request.scope_key, validity, provenance))
    relations: list[RelationInstance] = []
    factors: list[EquilibriumFactor] = []
    node_map = {item.node_id: item for item in nodes}
    for row in raw_factors:
        public_body = str(row["id"])
        inputs = tuple(public_to_exact[str(item)] for item in row["inputs"])
        outcome = public_to_exact[str(row["outcome"])]
        factor = EquilibriumFactor(
            _relation_id(request, public_body), inputs, outcome, int(row.get("polarity", 1)),
            float(row.get("authority", 1.0)), float(row.get("confidence", 1.0)), float(row.get("base_weight", 1.0)),
            str(row.get("source_key", request.source_id)), str(row.get("scope_key", request.scope_key)),
            row.get("valid_from", request.valid_from), row.get("valid_to", request.valid_to),
        )
        factors.append(factor)
        relation_type = "implies" if len(inputs) == 1 else "conjoins"
        arguments = tuple(RoleBinding("premise", item) for item in inputs) + (RoleBinding("conclusion", outcome),)
        relation = RelationInstance(factor.body_id, 2, relation_type, arguments, factor.scope_key, ValidityInterval(factor.valid_from, factor.valid_to), factor.confidence, factor.authority, provenance)
        validate_relation(relation, node_map)
        relations.append(relation)
    return CandidateTransaction(transaction_id, request.tenant_id, request.reality_id, request.source_id, source_text, tuple(nodes), tuple(relations), tuple(atoms), tuple(factors))


@lru_cache(maxsize=1)
def _conversation_runtime(root: str):
    from ltm.local_archive import resolve_archived_path
    from topology_g213.encoder import assert_model_hashes
    from topology_g213.inference import load_checkpoint

    repository = Path(root)
    config_path = repository / "configs/topology-g2-14.json"
    calibration_path = repository / "workspaces/topology-g2-14-r3/calibration.json"
    frozen_path = repository / "workspaces/topology-g2-14-r3/frozen-manifest.json"
    configuration = json.loads(config_path.read_text(encoding="utf-8"))
    calibration = json.loads(calibration_path.read_text(encoding="utf-8"))
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    checkpoint = resolve_archived_path(configuration["frozen_checkpoint"], repository)
    if not checkpoint.exists():
        raise ValueError("FROZEN_G213_CHECKPOINT_MISSING")
    file_hash = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    if file_hash(config_path) != frozen["config_sha256"] or file_hash(calibration_path) != frozen["calibration_sha256"] or file_hash(checkpoint) != frozen["checkpoint_sha256"]:
        raise ValueError("FROZEN_G214_HASH_MISMATCH")
    assert_model_hashes(repository / ".models/all-MiniLM-L6-v2")
    return load_checkpoint(checkpoint), calibration["thresholds"]


def _conversation(request: IngestRequest, source_text: str, transaction_id: str, root: Path) -> CandidateTransaction | CompileResult:
    # The runtime boundary requires supplied semantic spans.  The frozen gate
    # can only reduce the authority of this supplied interpretation.
    spans = request.payload.get("semantic_spans")
    if not isinstance(spans, list) or not spans:
        return _result("quarantine", transaction_id, ("SEMANTIC_SPANS_REQUIRED",))
    from topology_g213.schemas import ConversationCase, ConversationSpan, ConversationTurnSource
    from topology_g214.gate import gate_case
    from topology_g214.schemas import GateCandidate, GateCase

    if len(spans) > 8 or len(request.payload.get("candidates", ())) > 16:
        return _result("quarantine", transaction_id, ("BOUNDED_INPUT_EXCEEDED",))
    session_id = request.session_id or "sessionless"
    episode_id = str(request.payload.get("episode_id", session_id))
    source = ConversationTurnSource(request.source_id, session_id, episode_id, int(request.payload.get("turn_index", 0)), "user", source_text, request.source_hash)
    public_spans = tuple(ConversationSpan(
        str(row.get("id", f"span-{index}")), str(row["text"]), int(row["start"]), int(row["end"]), str(row.get("slot_type", "content")),
    ) for index, row in enumerate(spans))
    # Label fields are neutral constructor placeholders; gate inference reads
    # only public source text/spans and never treats these values as gold.
    case = ConversationCase(source, public_spans, "statement", "none", "none", "positive", "asserted", "session", "accept")
    candidates = tuple(GateCandidate(
        str(row["object_id"]), str(row["object_kind"]), str(row["alias"]), str(row["session_id"]),
        str(row.get("episode_id", episode_id)), str(row.get("scope_id", "session")), bool(row.get("active", True)) and str(row["object_kind"]) != "assistant_response",
        bool(row.get("expired", False)), bool(row.get("superseded", False)), bool(row.get("deleted", False)), int(row.get("recency", 0)),
    ) for row in request.payload.get("candidates", ()))
    try:
        model, thresholds = _conversation_runtime(str(root))
        gated = gate_case(model, GateCase(case, candidates), confidence_threshold=thresholds["confidence"], margin_threshold=thresholds["margin"], identity_confidence=thresholds["identity_confidence"], identity_margin=thresholds["identity_margin"])
    except (OSError, RuntimeError, ValueError) as exc:
        return _result("quarantine", transaction_id, (str(exc),))
    if gated.final_disposition != "accept":
        return _result(gated.final_disposition, transaction_id, gated.failure_codes, evidence_hash=gated.acceptance_evidence.evidence_hash)
    act = gated.original_prediction.act
    action = gated.original_prediction.action
    primary = next((row for row in spans if row.get("slot_type") == "content"), spans[0])
    content = str(primary.get("text", "")).strip()
    if not content:
        return _result("quarantine", transaction_id, ("EMPTY_CONTENT_SPAN",))
    provenance = _provenance(request, source_text)
    validity = ValidityInterval(request.valid_from, request.valid_to)
    kind = NodeKind.PREFERENCE if action == "set_preference" else NodeKind.QUESTION if act == "question" else NodeKind.CLAIM
    public_id = str(request.payload.get("event_id", transaction_id))
    attributes: dict[str, Any] = {
        "content": content, "discourse_act": act, "memory_action": action,
        "public_id": public_id, "user_reported": kind == NodeKind.CLAIM,
        "factual_authority": False,
    }
    if action == "set_preference":
        predicted_slots = dict(gated.original_prediction.slot_types)
        key = next((span.text for span in public_spans if predicted_slots.get(span.span_id) == "preference_key"), None)
        value = next((span.text for span in public_spans if predicted_slots.get(span.span_id) == "preference_value"), None)
        if not key or not value:
            return _result("clarification_required", transaction_id, ("PREFERENCE_SLOTS_REQUIRED",))
        attributes.update(preference_key=str(key), preference_value=str(value))
    target_ids = gated.authorized_target_ids
    if action in {"correct", "retract"} and len(target_ids) != 1:
        return _result("clarification_required", transaction_id, ("UNIQUE_TARGET_REQUIRED",))
    node = TopologyNode(_node_id(request, public_id), 2, kind, _attrs(attributes), request.scope_key, validity, provenance)
    event = {
        "action": action, "act": act, "content": content, "node_id": node.node_id,
        "target_ids": target_ids, "session_id": request.session_id,
        "evidence_hash": gated.acceptance_evidence.evidence_hash,
        "user_reported": kind == NodeKind.CLAIM, "factual_authority": False,
    }
    if action == "set_preference":
        event.update(preference_key=str(attributes["preference_key"]), preference_value=str(attributes["preference_value"]))
    return CandidateTransaction(transaction_id, request.tenant_id, request.reality_id, request.source_id, source_text, (node,), (), conversation_event=tuple(sorted(event.items())))


def compile_ingest(request: IngestRequest, root: Path) -> tuple[CompileResult, CandidateTransaction | None]:
    transaction_id = stable_id("parasite-transaction-v1", request.tenant_id, request.reality_id, request.source_id, request.source_hash, request.input_kind)
    try:
        source_text = _source_text(request)
        if hashlib.sha256(source_text.encode("utf-8")).hexdigest() != request.source_hash:
            raise ValueError("SOURCE_HASH_MISMATCH")
        if request.input_kind == "topology_document":
            candidate: CandidateTransaction | CompileResult = _topology(request, source_text, transaction_id)
        elif request.input_kind == "mathematical_reality":
            candidate = _math(request, source_text, transaction_id)
        else:
            candidate = _conversation(request, source_text, transaction_id, root)
        if isinstance(candidate, CompileResult):
            return candidate, None
        semantic = digest({"nodes": candidate.nodes, "relations": candidate.relations, "atoms": candidate.equilibrium_atoms, "factors": candidate.equilibrium_factors})
        return CompileResult("accept", transaction_id, semantic, None, (), (("input_kind", request.input_kind),)), candidate
    except (KeyError, TypeError, ValueError) as exc:
        return _result("quarantine", transaction_id, (str(exc),)), None
