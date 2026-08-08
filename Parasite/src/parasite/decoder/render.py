"""Render only independently authorized bundles."""

from __future__ import annotations

from parasite.contracts import RuntimeResult


def _text(disposition: str, claims: tuple[str, ...], alternatives: tuple[str, ...], support: tuple[str, ...], opposition: tuple[str, ...], tension: float, verified: bool, style: str) -> str:
    if disposition == "candidate":
        conclusion = claims[0] if claims else "No conclusion"
        if style == "brief":
            return f"Conclusion: {conclusion}. Verified: {'yes' if verified else 'no'}. Tension: {tension:.3f}."
        return "\n".join((
            f"Conclusion: {conclusion}", f"Support: {', '.join(support) or 'none'}",
            f"Opposition: {', '.join(opposition) or 'none'}", f"Tension: {tension:.6f}",
            f"Verification: {'passed' if verified else 'failed'}",
        ))
    if disposition == "alternatives":
        return f"Alternatives: {', '.join(alternatives)}. Residual tension: {tension:.3f}."
    if disposition == "clarification_required":
        return "Clarification is required; no active state was changed."
    if disposition == "quarantine":
        return "The input was quarantined; no active state was changed."
    if disposition.startswith("incomplete"):
        return "No answer was authorized because execution was incomplete."
    if disposition == "verification_failed":
        return "No answer was authorized because independent verification failed."
    return "The current reality does not support an answer."


def decode(
    *, disposition: str, claims: tuple[str, ...] = (), alternatives: tuple[str, ...] = (),
    support: tuple[str, ...] = (), opposition: tuple[str, ...] = (), tension: float = 0.0,
    certificate: tuple[str, ...] = (), verified: bool = False, trace: tuple[tuple[str, object], ...] = (),
    failures: tuple[str, ...] = (), style: str = "brief", renderer=None,
) -> RuntimeResult:
    deterministic = _text(disposition, claims, alternatives, support, opposition, tension, verified, style)
    response = deterministic
    if renderer is not None and verified:
        proposal = renderer({
            "disposition": disposition, "authorized_claims": claims, "alternatives": alternatives,
            "supporting_sources": support, "opposing_sources": opposition, "tension": tension,
        })
        # Optional language is accepted only with an explicit claim inventory
        # identical to the authorized bundle. Otherwise deterministic fallback.
        if isinstance(proposal, dict) and tuple(proposal.get("claims", ())) == claims and isinstance(proposal.get("text"), str):
            response = proposal["text"]
    return RuntimeResult(disposition, claims, alternatives, support, opposition, tension, certificate, response, trace, failures)

