"""Public-only latent-guided exact proof search for I3."""

from __future__ import annotations

import torch

from .dataset import expression_feature
from .formal import enumerate_applications, expression_hash
from .kernel import ProofKernel
from .schemas import (
    AxiomSchema,
    FormalProofStep,
    MathematicalInferenceResult,
    ProofState,
    TheoremProblem,
)


def _state(value, goal, used=()) -> ProofState:
    return ProofState(value, goal, tuple(used), expression_hash(value))


def _potentials(values, goal, model: ProofKernel) -> list[float]:
    """Return the learned proof-prefix potential for a batch of exact states.

    The formal kernel decides whether a rewrite exists; this potential is the
    only search-energy signal.  Keeping it batched is important: each proposal
    is scored in the same learned coordinate system before the beam is pruned.
    """
    if not values:
        return []
    state = torch.stack([torch.from_numpy(expression_feature(value)) for value in values])
    goal_feature = torch.from_numpy(expression_feature(goal))[None, :].expand(len(values), -1)
    with torch.no_grad():
        return [float(value) for value in model.potential(state, goal_feature).tolist()]


def infer(
    problem: TheoremProblem,
    schemas: tuple[AxiomSchema, ...],
    model: ProofKernel,
    *,
    use_model: bool = True,
    use_goal: bool = True,
    use_energy: bool = True,
) -> MathematicalInferenceResult:
    if any(item.relation == "neq" and item.left == problem.goal.left and item.right == problem.goal.right for item in problem.assumptions):
        return MathematicalInferenceResult(problem.problem_id, "refuted", (), (), 0, (), ())
    if problem.goal.relation != "eq":
        return MathematicalInferenceResult(problem.problem_id, "unknown", (), (), 0, (), ("UNSUPPORTED_GOAL",))
    goal = problem.goal.right
    scoring_goal = goal if use_goal else problem.goal.left
    initial = _state(problem.goal.left, goal)
    initial_energy = _potentials([initial.current], scoring_goal, model)[0] if use_energy else 0.0
    beam: list[tuple[ProofState, tuple[FormalProofStep, ...], float]] = [(initial, (), initial_energy)]
    visited = {initial.state_hash}
    opened: set[str] = set()
    energies: list[float] = [beam[0][2]]
    state_feature_goal = torch.from_numpy(expression_feature(scoring_goal)[None, :])
    for _ in range(problem.maximum_steps):
        proposals: list[tuple[float, ProofState, tuple[FormalProofStep, ...], float, str]] = []
        for state, proof, current_energy in beam:
            state_feature = torch.from_numpy(expression_feature(state.current)[None, :])
            with torch.no_grad():
                logits = model.logits(state_feature, state_feature_goal)[0].tolist() if use_model else [0.0] * len(schemas)
            ranked = sorted(range(len(schemas)), key=lambda index: (-float(logits[index]), schemas[index].axiom_id))[:8]
            exact_applications: list[tuple[int, AxiomSchema, tuple[int, ...], bool, object]] = []
            for index in ranked:
                schema = schemas[index]
                if schema.reality_key != problem.reality_key:
                    continue
                opened.add(schema.axiom_id)
                for path, reverse, after in enumerate_applications(state.current, schema):
                    # The frozen primary corpus is constructed as a
                    # complexity-reducing formal proof fragment. Reverse
                    # expansion remains available to the generator and exact
                    # verifier, but is not a runtime search shortcut.
                    if reverse:
                        continue
                    key = expression_hash(after)
                    if key in visited:
                        continue
                    exact_applications.append((index, schema, path, reverse, after))
                    if len(exact_applications) == 48:
                        break
                if len(exact_applications) == 48:
                    break
            after_energies = _potentials([item[4] for item in exact_applications], scoring_goal, model) if use_energy else [0.0] * len(exact_applications)
            for (index, schema, path, reverse, after), next_energy in zip(exact_applications, after_energies, strict=True):
                if use_energy and next_energy > current_energy + 1e-8:
                    continue
                step = FormalProofStep(schema.axiom_id, path, reverse, state.current, after)
                next_state = _state(after, goal, state.used_axiom_ids + (schema.axiom_id,))
                score = float(logits[index]) - next_energy
                proposals.append((score, next_state, proof + (step,), next_energy, schema.axiom_id))
            if len(proposals) >= 256:
                break
        if not proposals:
            break
        proposals.sort(key=lambda item: (-item[0], item[1].state_hash, item[4]))
        beam = []
        for _, state, proof, energy, _ in proposals:
            if state.state_hash in visited:
                continue
            visited.add(state.state_hash)
            beam.append((state, proof, energy))
            if state.current == goal:
                proof_energies = tuple(_potentials([item.before for item in proof] + [goal], goal, model)) if use_energy else tuple(0.0 for _ in range(len(proof) + 1))
                return MathematicalInferenceResult(problem.problem_id, "proved", proof, tuple(sorted(opened)), len(visited), proof_energies, ())
            if len(beam) == 4:
                break
        if not beam:
            break
        energies.append(min(item[2] for item in beam))
    return MathematicalInferenceResult(problem.problem_id, "unknown", (), tuple(sorted(opened)), len(visited), tuple(energies), ("NO_CERTIFIED_PROOF",))
