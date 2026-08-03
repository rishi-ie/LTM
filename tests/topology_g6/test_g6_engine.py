from topology_g6.engine import execute
from topology_g6.schemas import ReasoningProblem, Rule
from topology_g6.verifier import verify


def test_directional_chain_derives_only_forward():
    problem = ReasoningProblem("p", "implication", ("a",), (Rule("r1", "implies", ("a",), "b"), Rule("r2", "implies", ("b",), "goal")), "goal", depth=2)
    result = execute(problem)
    assert result.conclusion == "entailed"
    assert verify(problem, result) == (True, None)


def test_conjunction_requires_all_premises():
    problem = ReasoningProblem("p", "conjunction", ("a",), (Rule("r", "conjoins", ("a", "b"), "goal"),), "goal")
    assert execute(problem).conclusion == "unknown"
