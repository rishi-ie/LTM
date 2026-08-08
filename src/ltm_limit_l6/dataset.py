"""Deterministic L6 mathematical realities and query-independent fields."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np

from ltm_inference_i3.formal import FormalExpression, expression_hash

from .field import L6Field, build_field
from .optimizer import _hash_vector
from .schemas import (
    MathematicalEquilibriumPrompt,
    MathematicalQuerySlot,
    MathematicalRealityBody,
    RealityLawProfile,
)


def atom(name: str) -> FormalExpression:
    return FormalExpression("symbol", value=name)


@dataclass(frozen=True, slots=True)
class GeneratedCase:
    prompt: MathematicalEquilibriumPrompt
    field: L6Field
    expected_candidate: str | None
    expected_disposition: str
    depth: int
    family: str


def _body(body_id: str, reality: str, left: FormalExpression, right: FormalExpression, ref: int, *, polarity: int = 1, weight: float = 1.0, authority: float = 1.0, source: str | None = None) -> MathematicalRealityBody:
    return MathematicalRealityBody.make(body_id, reality, (left,), (right,), ref, weight, authority, polarity=polarity, source=source or body_id)


def build_case(depth: int, *, seed: int = 1960, reality_key: str = "standard", contradiction: bool = False, balanced: bool = False, unknown: bool = False, distractors: int = 32) -> GeneratedCase:
    if not 1 <= depth <= 20:
        raise ValueError("L6 case depth must be 1..20")
    bodies: list[MathematicalRealityBody] = []
    vector_rows: list[np.ndarray] = []
    chain = [atom(f"l6_{seed}_{index}") for index in range(depth + 1)]
    ref = 0
    for index in range(depth):
        vector_rows.extend((_hash_vector(expression_hash(chain[index])), _hash_vector(expression_hash(chain[index + 1]))))
        bodies.append(_body(f"body:{seed}:{index}", reality_key, chain[index], chain[index + 1], ref, weight=0.8 + (index % 3) * 0.05, authority=1.0, source=f"source:{seed}:{index}"))
        ref += 2
    # The formal query is public, just as a theorem goal is public.  The
    # evaluator-only expectation below is kept separately from runtime
    # routing; it is not used by field retrieval.
    expected = None if unknown else expression_hash(chain[-1])
    family = "unknown" if unknown else "chain"
    if contradiction:
        opposing = [atom(f"opp_{seed}_{index}") for index in range(depth + 1)]
        for index in range(depth):
            outcome = chain[-1] if balanced and index == depth - 1 else opposing[index + 1]
            vector_rows.extend((_hash_vector(expression_hash(chain[index])), _hash_vector(expression_hash(outcome))))
            bodies.append(_body(f"opp:{seed}:{index}", reality_key, chain[index], outcome, ref, polarity=-1, weight=0.4 if not balanced else 1.0, authority=0.7 if not balanced else 1.0, source=f"opp-source:{seed}:{index}"))
            ref += 2
        family = "balanced_contradiction" if balanced else "weighted_contradiction"
    for index in range(distractors):
        left, right = atom(f"distractor:{seed}:{index}"), atom(f"distractor:{seed}:{index}:out")
        vector_rows.extend((_hash_vector(expression_hash(left)), _hash_vector(expression_hash(right))))
        bodies.append(_body(f"distractor:{seed}:{index}", reality_key, left, right, ref, weight=0.1, authority=0.2, source=f"distractor-source:{seed}:{index}"))
        ref += 2
    # Custom realities use the same field shape but different signed manifests.
    if unknown:
        # A real unsupported query has no final transition, rather than a
        # reachable chain whose evaluator simply calls it unknown.
        bodies = [body for body in bodies if body.body_id != f"body:{seed}:{depth - 1}"]
    prompt_anchor = _hash_vector(expression_hash(chain[0]))
    prompt = MathematicalEquilibriumPrompt(f"prompt:{seed}:{depth}:{reality_key}", (chain[0],), MathematicalQuerySlot(chain[-1], "symbol", "equivalence"), reality_key, "global", None, tuple(float(x) for x in prompt_anchor))
    vectors = np.asarray(vector_rows, dtype=np.float32)
    field = build_field(tuple(bodies), vectors)
    return GeneratedCase(prompt, field, expected, "unknown" if unknown else "alternatives" if balanced else "candidate", depth, family)


def iter_cases(count: int, *, seed: int = 1960) -> tuple[GeneratedCase, ...]:
    return tuple(build_case(index % 20 + 1, seed=seed + index, contradiction=index % 7 == 0, balanced=index % 19 == 0, unknown=index % 23 == 0) for index in range(count))


def reality_profile(reality_key: str = "standard") -> RealityLawProfile:
    return RealityLawProfile(reality_key, "ltm-causal-reality/1", hashlib.sha256(f"{reality_key}:l4-executable-manifest".encode()).hexdigest())
