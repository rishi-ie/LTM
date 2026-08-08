"""Small deterministic development panel for the current L2 baseline."""

from __future__ import annotations

from ltm_r2.codec import archive_hash, artifact_hash, semantic_hash

from .compiler import compile_question, compile_statement, source
from .runtime import prove

_RULES = (
    ("x + 0 = x", "5 + 0 = 5"),
    ("0 + x = x", "0 + 5 = 5"),
    ("x * 1 = x", "5 * 1 = 5"),
    ("1 * x = x", "1 * 5 = 5"),
    ("x * 0 = 0", "5 * 0 = 0"),
    ("x plus 0 equals x", "7 plus 0 equals 7"),
    ("0 added to x equals x", "0 added to 7 equals 7"),
    ("x multiplied by 1 equals x", "7 multiplied by 1 equals 7"),
    ("1 times x equals x", "1 times 7 equals 7"),
    ("x times 0 equals 0", "7 times 0 equals 0"),
)


def _rate(passed: int, total: int) -> float:
    return round(passed / total, 6) if total else 1.0


def run_development_panel() -> dict[str, object]:
    registered = []
    for index, (rule_text, question_text) in enumerate(_RULES):
        statement = compile_statement(source(rule_text, source_id=f"dev:rule:{index}"))
        question = compile_question(source(question_text, source_id=f"dev:question:{index}"))
        proof = prove(question, (statement.body,)) if statement.body is not None else None
        round_trip = bool(statement.mumbrane_program is not None and (
            semantic_hash(statement.mumbrane_program)
            and artifact_hash(statement.mumbrane_program)
            and archive_hash(statement.mumbrane_program)
        ))
        registered.append({
            "statement": statement.disposition == "accept" and statement.evidence.statement_kind == "registered_rule",
            "question": question.disposition == "accept",
            "proof": bool(proof and proof.disposition == "proved" and proof.replay_valid),
            "round_trip": round_trip,
        })

    custom_preview = compile_statement(source("x + 2 = x", source_id="dev:custom", reality_key="custom-v1"))
    custom_active = compile_statement(source("x + 2 = x", source_id="dev:custom", reality_key="custom-v1"), confirmed=True)
    open_ended = tuple(compile_question(source(text, source_id=f"dev:open:{index}")) for index, text in enumerate((
        "simplify (x + 0)", "solve x + 1", "what is 5 + 0", "find x * 1", "calculate 7 + 2",
    )))
    malformed = tuple(compile_question(source(text, source_id=f"dev:bad:{index}")) for index, text in enumerate((
        "x + = x", "x + 0", "x + 0 = x;", "(x + 0 = x", "x ** 0 = x",
    )))
    total = len(registered)
    metrics = {
        "registered_statement_precision": _rate(sum(item["statement"] for item in registered), total),
        "explicit_question_acceptance": _rate(sum(item["question"] for item in registered), total),
        "verified_proof_replay": _rate(sum(item["proof"] for item in registered), total),
        "mumbrane_hash_boundary_checks": _rate(sum(item["round_trip"] for item in registered), total),
        "custom_confirmation_safety": float(custom_preview.disposition == "clarification_required" and custom_active.disposition == "accept"),
        "open_ended_abstention": _rate(sum(item.disposition == "clarification_required" for item in open_ended), len(open_ended)),
        "malformed_input_abstention": _rate(sum(item.disposition == "clarification_required" for item in malformed), len(malformed)),
    }
    return {
        "status": "development-baseline",
        "classification": "unclassified",
        "locked_result": False,
        "cases": {"registered_rules": total, "open_ended": len(open_ended), "malformed": len(malformed), "custom_confirmation": 2},
        "metrics": metrics,
        "limitations": (
            "small arithmetic panel; no split-disjoint locked data; no learned MiniLM compiler; "
            "no full fragment coverage; no calibrated end-to-end result"
        ),
    }
