"""Optional verified FLAN candidate ranking; it never invents a claim."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def _scorer(model_path: str):
    from topology_g101.model import FlanCandidateScorer

    return FlanCandidateScorer(Path(model_path))


def renderer(model_path: Path):
    """Return a renderer over candidates constructed from authorized claims only."""
    def render(bundle: dict):
        claims = tuple(bundle["authorized_claims"])
        if not claims:
            return {"claims": claims, "text": "No factual conclusion was authorized."}
        support = tuple(bundle["supporting_sources"])
        candidates = (
            f"Conclusion: {claims[0]}.",
            f"The verified conclusion is {claims[0]}." + (f" Supporting sources: {', '.join(support)}." if support else ""),
        )
        meaning = f"authorized claims: {claims}; support: {support}; tension: {bundle['tension']}"
        ranked = sorted((_scorer(str(model_path)).score(meaning, text)[0], text) for text in candidates)
        return {"claims": claims, "text": ranked[-1][1]}

    return render
