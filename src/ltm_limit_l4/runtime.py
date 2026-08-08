"""Public-only exact branching search with learned proposal ordering."""

from __future__ import annotations

import hashlib

import numpy as np
import torch

from ltm_inference_i3.dataset import expression_feature
from ltm_inference_i3.formal import expression_hash
from ltm_inference_i31.dataset import feature as r13_feature

from .axioms import executable_axioms
from .exact import enumerate_proposals, explicit_refutation, well_formed
from .kernel import BranchingProofKernel, schema_features, site_feature
from .schemas import (
    ExactAxiomApplication,
    L4InferenceResult,
    L4Problem,
    L4ProofStep,
    L4SearchTrace,
    Proposal,
)


def _application(before, proposal: Proposal) -> ExactAxiomApplication:
    return ExactAxiomApplication(
        proposal.body_id,
        proposal.axiom_id,
        proposal.path,
        proposal.reverse,
        proposal.substitution_hash,
        expression_hash(before),
        expression_hash(proposal.after),
    )


def _random_score(problem_id: str, state_hash: str, proposal: Proposal) -> float:
    digest = hashlib.sha256(
        repr((problem_id, state_hash, proposal.axiom_id, proposal.path, proposal.reverse)).encode()
    ).digest()
    return int.from_bytes(digest[:8], "little") / 2**64


def _l4_scores(model: BranchingProofKernel, state, goal, proposals: tuple[Proposal, ...], *, use_goal: bool, use_value: bool) -> tuple[list[float], list[float]]:
    if not proposals:
        return [], []
    schemas = schema_features()
    scoring_goal = goal if use_goal else state
    state_rows = torch.from_numpy(np.stack([expression_feature(state)] * len(proposals)))
    goal_rows = torch.from_numpy(np.stack([expression_feature(scoring_goal)] * len(proposals)))
    after_rows = torch.from_numpy(np.stack([expression_feature(item.after) for item in proposals]))
    schema_rows = torch.from_numpy(np.stack([schemas[item.axiom_id] for item in proposals]))
    site_rows = torch.from_numpy(
        np.stack([site_feature(item.path, item.reverse, state, item.after) for item in proposals])
    )
    with torch.no_grad():
        scores = model.proposal_score(state_rows, goal_rows, after_rows, schema_rows, site_rows).tolist()
        values = model.remaining_cost(after_rows, goal_rows).tolist() if use_value else [0.0] * len(proposals)
    return [float(item) for item in scores], [float(item) for item in values]


def _r13_scores(model, state, goal, proposals: tuple[Proposal, ...], *, use_goal: bool, use_value: bool) -> tuple[list[float], list[float]]:
    schemas = {item.axiom_id: item for item in executable_axioms()}
    scoring_goal = goal if use_goal else state
    state_rows = torch.from_numpy(np.stack([r13_feature(state)] * len(proposals)))
    goal_rows = torch.from_numpy(np.stack([r13_feature(scoring_goal)] * len(proposals)))
    body_rows = torch.from_numpy(
        np.stack(
            [
                np.concatenate((r13_feature(schemas[item.axiom_id].left), r13_feature(schemas[item.axiom_id].right)))
                for item in proposals
            ]
        )
    )
    after_rows = torch.from_numpy(np.stack([r13_feature(item.after) for item in proposals]))
    with torch.no_grad():
        scores = model.body_score(state_rows, goal_rows, body_rows).tolist()
        values = model.remaining_cost(after_rows, goal_rows).tolist() if use_value else [0.0] * len(proposals)
    return [float(item) for item in scores], [float(item) for item in values]


def infer(
    problem: L4Problem,
    model,
    *,
    track: str = "l4",
    use_scorer: bool = True,
    use_goal: bool = True,
    use_value: bool = True,
    random_scorer: bool = False,
    beam_width: int | None = None,
    first_candidate: bool = False,
) -> L4InferenceResult:
    torch.set_num_threads(4)
    if not well_formed(problem.source) or not well_formed(problem.goal):
        return L4InferenceResult(problem.problem_id, "quarantine", (), 0, (), (), ("INVALID_FORMAL_AST",))
    if explicit_refutation(problem.source, problem.goal):
        return L4InferenceResult(problem.problem_id, "refuted", (), 1, (), (), ())
    if problem.source == problem.goal:
        return L4InferenceResult(problem.problem_id, "proved", (), 1, (), (), ())
    width = min(beam_width or problem.beam_width, problem.beam_width)
    beam: list[tuple[object, tuple[L4ProofStep, ...], float]] = [(problem.source, (), 0.0)]
    visited = {expression_hash(problem.source)}
    opened: set[str] = set()
    traces: list[L4SearchTrace] = []
    for search_step in range(problem.maximum_steps):
        next_rows: list[tuple[float, object, tuple[L4ProofStep, ...], ExactAxiomApplication]] = []
        for state, proof, _ in beam:
            proposals = tuple(
                item for item in enumerate_proposals(state, reality_key=problem.reality_key)
                if expression_hash(item.after) not in visited
            )
            if len(proposals) > problem.maximum_legal_proposals:
                return L4InferenceResult(
                    problem.problem_id,
                    "quarantine",
                    (),
                    len(visited),
                    tuple(sorted(opened)),
                    tuple(traces),
                    ("PROPOSAL_BUDGET_EXCEEDED",),
                )
            if not proposals:
                continue
            opened.update(item.body_id for item in proposals)
            if random_scorer:
                scores = [_random_score(problem.problem_id, expression_hash(state), item) for item in proposals]
                values = [0.0] * len(proposals)
            elif not use_scorer:
                scores, values = [0.0] * len(proposals), [0.0] * len(proposals)
            elif track == "r13":
                scores, values = _r13_scores(model, state, problem.goal, proposals, use_goal=use_goal, use_value=use_value)
            else:
                scores, values = _l4_scores(model, state, problem.goal, proposals, use_goal=use_goal, use_value=use_value)
            ranked = sorted(
                zip(scores, values, proposals, strict=True),
                key=lambda row: (
                    len(proof) + 1 + row[1] - 0.25 * row[0],
                    row[2].axiom_id,
                    row[2].path,
                    expression_hash(row[2].after),
                ),
            )
            if first_candidate:
                ranked = ranked[:1]
            retained = ranked[:width]
            applications = tuple(_application(state, item[2]) for item in retained)
            traces.append(
                L4SearchTrace(
                    search_step,
                    expression_hash(state),
                    len(proposals),
                    applications,
                    tuple(expression_hash(item[2].after) for item in retained),
                    tuple(sorted({item.body_id for item in proposals})),
                )
            )
            for score, value, proposal in retained:
                application = _application(state, proposal)
                step = L4ProofStep(application, state, proposal.after)
                priority = len(proof) + 1 + value - 0.25 * score
                next_rows.append((priority, proposal.after, proof + (step,), application))
        if not next_rows:
            break
        next_rows.sort(key=lambda row: (row[0], expression_hash(row[1]), row[3].axiom_id))
        beam = []
        for priority, state, proof, _ in next_rows:
            key = expression_hash(state)
            if key in visited:
                continue
            visited.add(key)
            if state == problem.goal:
                return L4InferenceResult(
                    problem.problem_id,
                    "proved",
                    proof,
                    len(visited),
                    tuple(sorted(opened)),
                    tuple(traces),
                    (),
                )
            beam.append((state, proof, priority))
            if len(beam) == width:
                break
    return L4InferenceResult(
        problem.problem_id,
        "unknown",
        (),
        len(visited),
        tuple(sorted(opened)),
        tuple(traces),
        ("NO_VERIFIED_PATH",),
    )
