import numpy as np

from micro_ltm.oracle import label_for
from micro_ltm2.compress import compress
from micro_ltm2.field import codebook, fact_mask, relax
from micro_ltm2.generator import generate_split


def test_fresh_generator_balances_and_validates():
    problems = generate_split("test2", 12, 2729, range(4, 5), True)
    assert len(problems) == 24
    assert all(label_for(problem) == problem.gold_label for problem in problems)
    assert {problem.gold_label for problem in problems} == {"entailed", "contradicted", "unknown"}
    assert all(any(len(rule.premises) == 2 for rule in problem.rules) for problem in problems)


def test_facts_are_clamped_and_chain_is_monotonic():
    problem = generate_split("chain2", 3, 2730, range(8, 9), False)[0]
    codes = codebook(problem)
    result = relax(problem, codes)
    assert result.convergence_reason == "fixed_point"
    assert result.fixed_residual <= 1e-7
    assert np.all(result.final_activations >= fact_mask(problem))
    assert np.all(result.final_activations[0, problem.query_proposition] >= 0)
    assert all(step.max_delta >= 0 for step in result.trace)


def test_direction_is_not_used_by_forward_field():
    problem = generate_split("direction2", 3, 2730, range(4, 5), False)[2]
    codes = codebook(problem)
    forward = relax(problem, codes)
    reverse = relax(problem, codes, mode="reverse")
    assert forward.final_activations[0, problem.query_proposition] <= 0.5
    assert reverse.final_activations[0, problem.query_proposition] >= forward.final_activations[0, problem.query_proposition]


def test_compression_is_deterministic_and_target_neutral_at_start():
    problem = generate_split("compress2", 3, 2729, range(4, 5), False)[0]
    codes = codebook(problem)
    initial = compress(fact_mask(problem), codes, problem.query_proposition)
    repeated = compress(fact_mask(problem), codes, problem.query_proposition)
    np.testing.assert_array_equal(initial.state, repeated.state)
    assert np.isclose(np.linalg.norm(initial.state), 1.0)

