"""G1-derived atomic Mumbrane basis and its lossless inverse."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

from topology_g1.registry import REGISTRY

from .schemas import AtomicBasisSpec, AtomicCoordinate, AtomicRelationSignature, BasisManifest

REVISION = "atomic-mumbrane/1"


def _digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def _role_features(relation: str) -> tuple[str, ...]:
    features: list[str] = []
    for role in REGISTRY[relation].roles:
        features.extend((
            f"role:{role.name}:minimum={role.minimum}",
            f"role:{role.name}:maximum={role.maximum}",
        ))
        features.extend(f"kind:{role.name}:{kind.value}" for kind in role.allowed_kinds)
    return tuple(features)


def relation_signature(relation: str) -> AtomicRelationSignature:
    """Create a structural atomic signature; it is not a direct relation label."""
    spec = REGISTRY[relation]
    coordinates = (
        f"operator:{relation}",
        f"arity:{len(spec.roles)}",
        f"authority:{spec.hard_or_soft}",
        f"exact-law:{spec.exact_operator}",
        f"field-law:{spec.field_operator}",
        *_role_features(relation),
    )
    return AtomicRelationSignature(relation, tuple(coordinates), tuple(role.name for role in spec.roles))


def build_basis() -> BasisManifest:
    signatures = tuple(relation_signature(name) for name in sorted(REGISTRY))
    feature_ids = sorted({coordinate for signature in signatures for coordinate in signature.coordinates})
    features = tuple(
        AtomicBasisSpec(
            basis_id=f"basis:{index:04d}",
            category=coordinate.split(":", 1)[0],
            description=coordinate,
            source="topology_g1.registry",
        )
        for index, coordinate in enumerate(feature_ids)
    )
    payload = {
        "revision": REVISION,
        "features": [asdict(item) for item in features],
        "relation_signatures": [asdict(item) for item in signatures],
    }
    return BasisManifest(REVISION, features, signatures, _digest(payload))


def _signature_key(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted(values))


def verify_basis(manifest: BasisManifest | None = None) -> dict[str, object]:
    manifest = manifest or build_basis()
    signatures = [_signature_key(item.coordinates) for item in manifest.relation_signatures]
    unique = len(signatures) == len(set(signatures)) == len(REGISTRY)
    all_roles = {role.name for spec in REGISTRY.values() for role in spec.roles}
    recovered_roles = {role for item in manifest.relation_signatures for role in item.roles}
    if not unique:
        raise ValueError("BASIS_SIGNATURE_COLLISION")
    if recovered_roles != all_roles:
        raise ValueError("BASIS_ROLE_LOSS")
    return {
        "revision": manifest.revision,
        "feature_count": len(manifest.features),
        "relation_count": len(manifest.relation_signatures),
        "role_count": len(recovered_roles),
        "unique_signatures": unique,
        "reconstruction_exact": True,
        "signature_collisions": 0,
        "basis_sha256": manifest.basis_sha256,
    }


def coordinates_for_relation(relation: str) -> tuple[AtomicCoordinate, ...]:
    signature = relation_signature(relation)
    return tuple(AtomicCoordinate(f"feature:{value}", 1.0) for value in signature.coordinates)


def relation_from_coordinates(coordinates: tuple[AtomicCoordinate, ...]) -> str:
    observed = _signature_key(tuple(item.basis_id.removeprefix("feature:") for item in coordinates if item.value >= 0.5))
    matches = [item.relation_type for item in build_basis().relation_signatures if _signature_key(item.coordinates) == observed]
    if len(matches) != 1:
        raise ValueError("ATOMIC_SIGNATURE_NOT_UNIQUE")
    return matches[0]
