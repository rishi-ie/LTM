from __future__ import annotations

from dataclasses import replace

import numpy as np

from .decode import LogisticDecoder, features
from .optimize import optimize
from .schemas import FieldConfig, InterventionResult, MicroProblem


def decode_state(problem: MicroProblem, state: np.ndarray, codes: np.ndarray, decoder: LogisticDecoder) -> str:
    return decoder.predict(features(state, codes, problem.query_proposition)).label


def run_interventions(
    problem: MicroProblem,
    twin: MicroProblem,
    config: FieldConfig,
    decoder: LogisticDecoder,
    codes: np.ndarray,
) -> list[InterventionResult]:
    a = optimize(problem, config, codes=codes)
    b = optimize(twin, config, codes=codes)
    out: list[InterventionResult] = []
    pred_a = decode_state(problem, a.final_state, codes, decoder)
    pred_b = decode_state(twin, b.final_state, codes, decoder)
    out.append(InterventionResult("state_swap_a", pred_a, decode_state(problem, b.final_state, codes, decoder), twin.gold_label, pred_a == problem.gold_label and decode_state(problem, b.final_state, codes, decoder) == twin.gold_label))
    out.append(InterventionResult("state_swap_b", pred_b, decode_state(twin, a.final_state, codes, decoder), problem.gold_label, pred_b == twin.gold_label and decode_state(twin, a.final_state, codes, decoder) == problem.gold_label))
    if problem.decisive_rule_id:
        removed = replace(problem, rules=tuple(r for r in problem.rules if r.rule_id != problem.decisive_rule_id))
        removed_result = optimize(removed, config, codes=codes)
        removed_label = decode_state(removed, removed_result.final_state, codes, decoder)
        out.append(InterventionResult("remove_decisive_rule", problem.gold_label, removed_label, twin.gold_label, removed_label == twin.gold_label))
    if problem.decisive_rule_id:
        reversed_rules = tuple(
            replace(r, conclusion=replace(r.conclusion, polarity=-r.conclusion.polarity))
            if r.rule_id == problem.decisive_rule_id else r
            for r in problem.rules
        )
        reversed_problem = replace(problem, rules=reversed_rules)
        reversed_result = optimize(reversed_problem, config, codes=codes)
        reversed_label = decode_state(reversed_problem, reversed_result.final_state, codes, decoder)
        expected = "contradicted" if problem.gold_label == "entailed" else "entailed"
        out.append(InterventionResult("reverse_decisive_rule", problem.gold_label, reversed_label, expected, reversed_label == expected))
    return out
