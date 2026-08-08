from dataclasses import replace

from ltm_limit_l4.codec import problem_from_obj
from ltm_limit_l4.evaluator import verify_result
from ltm_limit_l4.generator import _problem
from ltm_limit_l4.kernel import BranchingProofKernel, parameter_count
from ltm_limit_l4.runtime import infer


def test_exact_search_replays_a_small_branching_proof() -> None:
    public, _ = _problem("runtime", 7, 17, depth=2, branching=4, family="logic")
    problem = problem_from_obj(public)
    result = infer(problem, None, use_scorer=False)
    assert result.disposition == "proved"
    assert verify_result(problem, result)
    assert result.factual_operations == ()


def test_explicit_negative_source_refutes_without_search() -> None:
    public, _ = _problem("refuted", 2, 19, depth=0, branching=2, family="ring", status="refuted")
    problem = problem_from_obj(public)
    result = infer(problem, None, use_scorer=False)
    assert result.disposition == "refuted"
    assert verify_result(problem, result)


def test_independent_replay_rejects_corrupt_step() -> None:
    public, _ = _problem("corrupt", 3, 23, depth=2, branching=4, family="sets")
    problem = problem_from_obj(public)
    result = infer(problem, None, use_scorer=False)
    step = result.proof[0]
    corrupt_application = replace(step.application, after_hash="0" * 64)
    corrupt = replace(result, proof=(replace(step, application=corrupt_application), *result.proof[1:]))
    assert not verify_result(problem, corrupt)


def test_kernel_fits_replacement_budget() -> None:
    model = BranchingProofKernel()
    assert parameter_count(model) <= 2_000_000
    assert sum(item.numel() * item.element_size() for item in model.parameters()) <= 8_000_000
