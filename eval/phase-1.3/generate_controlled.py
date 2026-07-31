"""Generate the deterministic controlled Phase 1.3 fixture.

Run from the repository root only when deliberately regenerating the locked
fixture; normal evaluation never calls this module.
"""

from __future__ import annotations

import json
from pathlib import Path

CATEGORIES = (
    "single_hop_paraphrase",
    "two_evidence_bridge",
    "three_evidence_bridge",
    "lexical_distractor",
    "semantic_distractor",
    "rare_terminology",
    "duplicate_density",
    "irrelevant_density",
    "equal_weight_contradiction",
    "unequal_authority_contradiction",
    "temporal_correction",
    "answer_not_present",
)


def build() -> dict[str, object]:
    domains = []
    for category in CATEGORIES:
        documents: dict[str, dict[str, object]] = {}
        cases = []
        for number in range(25):
            prefix = f"p13-{category}-{number:02d}"
            gold = [f"{prefix}-gold-{index}" for index in range(1, 4)]
            for index, chunk_id in enumerate(gold, start=1):
                documents[chunk_id] = {
                    "text": (
                        f"The {category} case {number} establishes evidence "
                        f"{index} for subject {number}."
                    ),
                    "metadata": {
                        "priority": 1.0,
                        "confidence": 1.0,
                        "authority": 1.0,
                        "recency": 1.0,
                    },
                }
            for index in range(8):
                chunk_id = f"{prefix}-distractor-{index:02d}"
                documents[chunk_id] = {
                    "text": (
                        f"Unrelated distractor {index} appears near subject "
                        f"{number} in the shared corpus."
                    ),
                    "metadata": {
                        "priority": 1.0,
                        "confidence": 1.0,
                        "authority": 1.0,
                        "recency": 1.0,
                    },
                }
            cases.append(
                {
                    "id": prefix,
                    "category": category,
                    "query": (
                        f"Which evidence supports the {category.replace('_', ' ')} "
                        f"case for subject {number}?"
                    ),
                    "gold": gold if category != "answer_not_present" else [],
                    "answer": f"Evidence for subject {number}.",
                }
            )
        domains.append({"id": category, "documents": documents, "cases": cases})
    return {"locked": True, "suite": "phase-1.3-controlled", "domains": domains}


if __name__ == "__main__":
    target = Path(__file__).with_name("controlled-held-out.json")
    target.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(target)
