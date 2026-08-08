"""Strict realization of independently verified L5 candidates."""

from __future__ import annotations

from dataclasses import dataclass

from .schemas import EquilibriumCandidate, FieldEquilibriumResult, SupportCertificate


@dataclass(frozen=True, slots=True)
class AuthorizedEquilibriumView:
    prompt_id: str
    disposition: str
    candidates: tuple[EquilibriumCandidate, ...]
    certificates: tuple[SupportCertificate, ...]


@dataclass(frozen=True, slots=True)
class EquilibriumRealization:
    prompt_id: str
    disposition: str
    authorized_unit_ids: tuple[str, ...]
    text: str
    failure_codes: tuple[str, ...]


def authorize(result: FieldEquilibriumResult) -> AuthorizedEquilibriumView:
    verified = {item.candidate_unit_id for item in result.certificates if item.verified}
    candidates = tuple(item for item in result.candidates if item.unit_id in verified)
    if result.selected_candidate_id is not None and result.selected_candidate_id not in verified:
        raise ValueError("UNVERIFIED_SELECTED_CANDIDATE")
    if result.disposition == "candidate":
        if result.selected_candidate_id is None:
            raise ValueError("AUTHORIZED_CANDIDATE_MISSING")
        candidates = tuple(
            item for item in candidates if item.unit_id == result.selected_candidate_id
        )
        if len(candidates) != 1:
            raise ValueError("AUTHORIZED_CANDIDATE_COUNT_MISMATCH")
    if result.disposition == "alternatives" and len(candidates) < 2:
        raise ValueError("AUTHORIZED_ALTERNATIVES_MISSING")
    return AuthorizedEquilibriumView(
        result.prompt_id,
        result.disposition,
        candidates,
        tuple(item for item in result.certificates if item.verified),
    )


def realize(view: AuthorizedEquilibriumView, surface_archive: dict[str, str]) -> EquilibriumRealization:
    missing = tuple(item.unit_id for item in view.candidates if item.semantic_key not in surface_archive)
    if missing:
        return EquilibriumRealization(
            view.prompt_id, "quarantine", (), "Unable to realize a verified field state.",
            ("AUTHORIZED_SURFACE_MISSING",),
        )
    labels = tuple(surface_archive[item.semantic_key] for item in view.candidates)
    if view.disposition == "candidate":
        text = labels[0]
    elif view.disposition == "alternatives":
        text = "Supported alternatives: " + "; ".join(labels)
    elif view.disposition == "ambiguous":
        text = "The field contains equally supported incompatible states."
    elif view.disposition == "incomplete_frontier":
        text = "The relevant field frontier could not be certified."
    elif view.disposition == "unknown":
        text = "The field does not contain enough support to answer."
    else:
        text = "The request was quarantined."
    return EquilibriumRealization(
        view.prompt_id,
        view.disposition,
        tuple(item.unit_id for item in view.candidates),
        text,
        (),
    )
