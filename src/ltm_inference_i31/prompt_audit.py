"""Single-prompt forensic audit for the I3.1 proof-to-answer path."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from ltm.adapters import from_g1
from ltm.codec import semantic_hash as field_semantic_hash
from ltm_r2.codec import semantic_hash as mumbrane_semantic_hash
from ltm_r2.generator import SemanticAtom, SemanticBody, SemanticRelation, compile_body
from topology_g1.registry import validate_relation
from topology_g1.schemas import (
    NodeKind,
    Provenance,
    RelationInstance,
    RoleBinding,
    TopologyNode,
    ValidityInterval,
)
from topology_g10.schemas import AuthorizedClaim, DecoderBundle, StateChannel
from topology_g101.model import FlanCandidateScorer
from topology_g101.realize import realize

from . import schemas
from .axioms import standard_axiom_bodies
from .dataset import feature
from .field import MathFieldIndex, build_field
from .kernel import SearchKernel
from .runtime import infer
from .schemas import PromptAuditRecord, SearchTraceEvent, VerifiedMathEnvelope


def _expr(value):
    return {"op": value.op, "value": value.value, "args": [_expr(item) for item in value.args]}


def _body_obj(body):
    return {"body_id": body.body_id, "reality_key": body.reality_key, "left": _expr(body.left), "right": _expr(body.right), "provenance_hash": body.provenance_hash, "vector_index": body.vector_index}


def _sha(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def _problem():
    from ltm_inference_i3.formal import FormalExpression
    def integer(value: int) -> FormalExpression:
        return FormalExpression("int", value=str(value))
    return schemas.TheoremProblem("prompt:5-plus-0-times-1", "standard-v1", FormalExpression("mul", (FormalExpression("add", (integer(5), integer(0))), integer(1))), integer(5), 64, 16)


def _field() -> MathFieldIndex:
    bodies = standard_axiom_bodies()
    import numpy as np
    vectors = np.asarray([np.concatenate((feature(body.left), feature(body.right))) for body in bodies], dtype=np.float32)
    return MathFieldIndex(bodies, vectors, build_field(bodies, vectors))


def _g1_certificate(problem, proof, proof_hash):
    source_id = _sha("math:expression:source")
    goal_id = _sha("math:expression:goal")
    source_hash = _sha(_expr(problem.source))
    provenance = Provenance("math-prompt", 0, 1, source_hash)
    nodes = (
        TopologyNode(source_id, 2, NodeKind.VALUE, (("expression", "The expression (5 plus 0) times 1"),), "standard-v1", ValidityInterval(), (provenance,)),
        TopologyNode(goal_id, 2, NodeKind.VALUE, (("expression", "5"),), "standard-v1", ValidityInterval(), (provenance,)),
    )
    relation = RelationInstance(_sha("math:certificate:equals"), 2, "equals", (RoleBinding("left", source_id), RoleBinding("right", goal_id)), "standard-v1", ValidityInterval(), 1.0, 1.0, (provenance,))
    validate_relation(relation, {item.node_id: item for item in nodes})
    return nodes, relation, from_g1(nodes, (relation,)), proof_hash


def _mumbrane_certificate(proof_hash: str):
    relation = SemanticRelation("math:equals", "equals", (("left", ("math:source",)), ("right", ("math:goal",))), 1.0, 0.0)
    body = SemanticBody("math:certificate", (SemanticAtom("math:source", "value"), SemanticAtom("math:goal", "value")), (relation,), "global", None, f"formal-proof:{proof_hash}")
    return compile_body(body)


def _decode(proof_hash: str) -> str:
    claim = AuthorizedClaim("math:claim", "The expression (5 plus 0) times 1", "equals", "5", "positive", "standard-v1", "certain", f"formal-proof:{proof_hash}")
    bundle = DecoderBundle("math:answer", "explanation", "Prove the equality.", "verified", (claim,), "multiplying by 1 gives 5 plus 0; adding 0 then gives 5", (), (), StateChannel(.99, .01, 0.0, 1.0, "answer", "explanatory"), "answer")
    return realize(bundle, FlanCandidateScorer(Path(".models/flan-t5-small"))).selected.text


def run(workspace: Path, checkpoint: Path) -> PromptAuditRecord:
    workspace.mkdir(parents=True, exist_ok=True)
    import torch
    model = SearchKernel()
    model.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True)); model.eval()
    field = _field(); problem = _problem(); trace: list[SearchTraceEvent] = []
    # This is the unchanged operational I3.1 path.  The remaining-cost head
    # stays enabled for the audit; its causal contribution is reported by the
    # existing controls and is not claimed from this single prompt.
    result = infer(problem, field, model, use_heuristic=True, use_scorer=True, prefer_reductions=False, trace_sink=trace.append)
    bodies = field.bodies
    proof_payload = [asdict(item) | {"before": _expr(item.before), "after": _expr(item.after)} for item in result.proof]
    proof_hash = _sha(proof_payload)
    replay_input = workspace / "replay-input.json"
    replay_input.write_text(json.dumps({"source": _expr(problem.source), "goal": _expr(problem.goal), "reality_key": problem.reality_key, "proof": proof_payload, "bodies": [_body_obj(bodies[item.body_id]) for item in result.proof]}, sort_keys=True), encoding="utf-8")
    replay_process = subprocess.run((sys.executable, "-m", "ltm_inference_i31.replay", str(replay_input)), check=True, capture_output=True, text=True)
    replay = bool(result.disposition == "proved" and json.loads(replay_process.stdout)["valid"])
    envelope = None
    field_hash = mumbrane_hash = decoder_text = None
    if replay:
        envelope = VerifiedMathEnvelope("math:envelope", problem.reality_key, _sha(_expr(problem.source)), _sha(_expr(problem.goal)), proof_hash, tuple(item.body_id for item in result.proof), "The expression (5 plus 0) times 1", "5", proof_hash)
        _, _, (field_program, _), _ = _g1_certificate(problem, result.proof, proof_hash)
        field_hash = field_semantic_hash(field_program)
        mumbrane_hash = mumbrane_semantic_hash(_mumbrane_certificate(proof_hash))
        decoder_text = _decode(proof_hash)
    controls: list[tuple[str, str, bool]] = []
    no_scorer = infer(problem, field, model, use_heuristic=False, use_scorer=False, prefer_reductions=False)
    controls.append(("scorer-disabled", no_scorer.disposition, no_scorer.disposition != "proved"))
    wrong = schemas.TheoremProblem(problem.problem_id, "wrong-reality", problem.source, problem.goal, 64, 16)
    wrong_result = infer(wrong, field, model, use_heuristic=False, use_scorer=True, prefer_reductions=False)
    controls.append(("wrong-reality", wrong_result.disposition, wrong_result.disposition != "proved"))
    changed = schemas.TheoremProblem(problem.problem_id, problem.reality_key, problem.source, __import__("ltm_inference_i3.formal", fromlist=["FormalExpression"]).FormalExpression("atom", value="6"), 64, 16)
    changed_result = infer(changed, field, model, use_heuristic=False, use_scorer=True, prefer_reductions=False)
    controls.append(("changed-goal", changed_result.disposition, changed_result.disposition != "proved"))
    record = PromptAuditRecord("In standard arithmetic, prove (5 + 0) × 1 = 5.", result, tuple(trace), replay, envelope, field_hash, mumbrane_hash, decoder_text, tuple(controls))
    (workspace / "input.json").write_text(json.dumps({"prompt": record.prompt_text, "problem": {"problem_id": problem.problem_id, "reality_key": problem.reality_key, "source": _expr(problem.source), "goal": _expr(problem.goal), "maximum_bodies": problem.maximum_bodies, "maximum_steps": problem.maximum_steps}}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (workspace / "runtime-trace.json").write_text(json.dumps([asdict(item) for item in trace], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (workspace / "proof-certificate.json").write_text(json.dumps({"proof_hash": proof_hash, "proof": proof_payload}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (workspace / "replay-result.json").write_text(json.dumps({"valid": replay, "process_isolated": True}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if envelope is not None:
        (workspace / "verified-envelope.json").write_text(json.dumps(asdict(envelope), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (workspace / "decoder-result.json").write_text(json.dumps({"text": decoder_text, "authorized": bool(decoder_text)}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (workspace / "audit-summary.json").write_text(json.dumps(asdict(record), default=str, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record


def main(workspace: Path, checkpoint: Path) -> int:
    record = run(workspace, checkpoint)
    print(json.dumps({"disposition": record.inference.disposition, "proof": [item.body_id for item in record.inference.proof], "replay_valid": record.replay_valid, "decoder_text": record.decoder_text, "controls": record.controls}, default=str, indent=2, sort_keys=True))
    return 0
