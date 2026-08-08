"""Data-only topology profiles and their numeric compiled form."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

from topology_g1.registry import REGISTRY

from .codebook import FEATURE_BITS, OPERATOR_CODES
from .schemas import MUMBRANE_SCHEMA, CompiledTopologyProfile, TopologyProfile

OPCODES = (
    "derive",
    "derive_all",
    "require",
    "exclude",
    "temporal_order",
    "supersede",
    "scope_gate",
    "reference_simplex",
    "provenance_link",
    "soft_attract",
    "soft_repel",
    "uncertainty",
    "preference",
    "causal_hypothesis",
)
OPCODE_CODES = {name: index + 1 for index, name in enumerate(OPCODES)}


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _profile(profile_id: str, active: tuple[str, ...], *, weight: float) -> TopologyProfile:
    if any(name not in REGISTRY for name in active):
        raise ValueError("unknown G1 operator in profile")
    exact = []
    soft = []
    for name in active:
        spec = REGISTRY[name]
        opcode = {
            "derive": "derive",
            "derive_all": "derive_all",
            "obligation": "require",
            "conflict": "exclude",
            "temporal": "temporal_order",
            "temporal_inverse": "temporal_order",
            "supersede": "supersede",
            "scope_gate": "scope_gate",
            "bind_reference": "reference_simplex",
            "provenance_link": "provenance_link",
            "assistant_link": "provenance_link",
        }.get(spec.exact_operator)
        if opcode:
            exact.append((name, opcode))
        soft_opcode = {
            "support": "soft_attract",
            "oppose": "soft_repel",
            "uncertainty_message": "uncertainty",
            "response_constraint": "preference",
            "hypothesis_message": "causal_hypothesis",
        }.get(spec.exact_operator)
        if soft_opcode:
            soft.append((name, soft_opcode))
    # The active relation units must expose executable topology bands.  Content
    # lives in target units and is validated through typed ports instead.
    required = sum(FEATURE_BITS[name] for name in ("operator", "role", "context", "provenance", "identity", "region", "integrity"))
    payload = {
        "profile_id": profile_id,
        "revision": "1",
        "schema": MUMBRANE_SCHEMA,
        "operators": active,
        "exact": exact,
        "soft": soft,
        "weight": weight,
    }
    return TopologyProfile(profile_id, "1", MUMBRANE_SCHEMA, "g1-operator-bank/1", active, tuple(exact), tuple(soft), required, weight, _digest(payload))


PROFILES = {
    "reasoning": _profile("reasoning", tuple(sorted(REGISTRY)), weight=1.0),
    "planning": _profile("planning", ("implies", "conjoins", "requires", "excludes", "before", "after", "supersedes", "prefers", "scoped_to"), weight=1.25),
    "evidence": _profile("evidence", ("supports", "opposes", "uncertainty", "causes_hypothetically", "derived_from", "before", "after", "scoped_to", "excludes"), weight=.8),
    "conversation": _profile("conversation", ("refers_to", "prefers", "supersedes", "scoped_to", "derived_from", "assistant_derived_from", "excludes"), weight=1.1),
}


def compile_profile(profile: TopologyProfile) -> CompiledTopologyProfile:
    if profile.mumbrane_schema_revision != MUMBRANE_SCHEMA:
        raise ValueError("PROFILE_SCHEMA_MISMATCH")
    if any(opcode not in OPCODE_CODES for _operator, opcode in (*profile.exact_opcodes, *profile.soft_opcodes)):
        raise ValueError("UNKNOWN_PROFILE_OPCODE")
    operator_codes = tuple(sorted(OPERATOR_CODES[name] for name in profile.active_operator_ids))
    opcode_codes = tuple(sorted(
        (OPERATOR_CODES[name], OPCODE_CODES[opcode], 1)
        for name, opcode in profile.exact_opcodes
    ) + sorted(
        (OPERATOR_CODES[name], OPCODE_CODES[opcode], 2)
        for name, opcode in profile.soft_opcodes
    ))
    execution_sha256 = _digest({"profile": asdict(profile), "operator_codes": operator_codes, "opcode_codes": opcode_codes})
    return CompiledTopologyProfile(profile, operator_codes, opcode_codes, execution_sha256)


def profile_named(name: str) -> CompiledTopologyProfile:
    try:
        return compile_profile(PROFILES[name])
    except KeyError as exc:
        raise ValueError("UNKNOWN_TOPOLOGY_PROFILE") from exc


def dynamics_variant(profile: TopologyProfile, multiplier: float) -> TopologyProfile:
    payload = {"base": profile.profile_sha256, "multiplier": multiplier}
    return TopologyProfile(
        profile.profile_id,
        f"{profile.revision}-dynamics",
        profile.mumbrane_schema_revision,
        profile.operator_bank_revision,
        profile.active_operator_ids,
        profile.exact_opcodes,
        profile.soft_opcodes,
        profile.required_feature_mask,
        profile.dynamics_weight * multiplier,
        _digest(payload),
    )
