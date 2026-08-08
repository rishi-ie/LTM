"""Evaluator-owned semantic bodies and deterministic Mumbrane compilation."""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass

from topology_g1.registry import REGISTRY

from .codebook import (
    AXIS_CODES,
    CLASS_CODES,
    FEATURE_BITS,
    NODE_CODES,
    OPERATOR_CODES,
    ROLE_CODES,
    feature_mask,
)
from .codec import digest, make_program
from .schemas import (
    MUMBRANE_SCHEMA,
    MumbraneCoordinate,
    MumbranePort,
    MumbraneProgram,
    MumbraneUnit,
    MumbraneVectorBundle,
)


@dataclass(frozen=True, slots=True)
class SemanticAtom:
    atom_id: str
    kind: str


@dataclass(frozen=True, slots=True)
class SemanticRelation:
    relation_id: str
    relation_type: str
    role_bindings: tuple[tuple[str, tuple[str, ...]], ...]
    base_weight: float
    geometry: float


@dataclass(frozen=True, slots=True)
class SemanticBody:
    body_id: str
    atoms: tuple[SemanticAtom, ...]
    relations: tuple[SemanticRelation, ...]
    scope: str
    session: str | None
    source_text: str


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _unit_hash(unit_id: str, class_code: int, semantic_code: int, mask: int) -> str:
    return _sha(f"{unit_id}|{class_code}|{semantic_code}|{mask}")


def _vector(seed: int, geometry: float) -> tuple[float, ...]:
    rng = random.Random(seed)
    return tuple(round((geometry if index == 0 else rng.uniform(-.5, .5)), 7) for index in range(8))


def _relation_atoms(body_id: str, relation: str, offset: int) -> tuple[SemanticAtom, tuple[tuple[str, tuple[str, ...]], ...]]:
    specification = REGISTRY[relation]
    atoms: list[SemanticAtom] = []
    bindings: list[tuple[str, tuple[str, ...]]] = []
    for role_index, role in enumerate(specification.roles):
        ids = []
        for ordinal in range(role.minimum):
            atom_id = f"{body_id}:a:{offset}:{role_index}:{ordinal}"
            atoms.append(SemanticAtom(atom_id, role.allowed_kinds[(role_index + ordinal) % len(role.allowed_kinds)].value))
            ids.append(atom_id)
        bindings.append((role.name, tuple(ids)))
    return tuple(atoms), tuple(bindings)


def make_body(index: int, *, seed: int) -> SemanticBody:
    """Create a complete, G1-valid semantic body before rendering any field."""
    rng = random.Random(seed + index * 7919)
    relation_names = tuple(sorted(REGISTRY))
    selected = [relation_names[index % len(relation_names)]]
    if index % 4 == 0:
        selected.append(relation_names[(index * 7 + 3) % len(relation_names)])
    if index % 13 == 0:
        selected.append(relation_names[(index * 11 + 5) % len(relation_names)])
    selected = list(dict.fromkeys(selected))[:3]
    body_id = f"body:{index:05d}"
    atoms: list[SemanticAtom] = []
    relations: list[SemanticRelation] = []
    for relation_index, relation in enumerate(selected):
        created, bindings = _relation_atoms(body_id, relation, relation_index)
        atoms.extend(created)
        relations.append(SemanticRelation(
            f"{body_id}:r:{relation_index}", relation, bindings,
            round(.4 + rng.random() * .6, 6), round(-.8 + rng.random() * 1.6, 6),
        ))
    # Extra independent content keeps every body multi-purpose rather than a single edge.
    while len(atoms) < 8:
        ordinal = len(atoms)
        atoms.append(SemanticAtom(f"{body_id}:extra:{ordinal}", "entity" if ordinal % 2 else "claim"))
    scope = ("global", "fictional", "session", "temporary")[index % 4]
    session = f"session:{index % 17}" if scope == "session" else None
    source = f"opaque semantic body {index}; archive only"
    return SemanticBody(body_id, tuple(atoms), tuple(relations), scope, session, source)


def build_bodies(count: int, *, seed: int) -> tuple[SemanticBody, ...]:
    return tuple(make_body(index, seed=seed) for index in range(count))


def compile_body(body: SemanticBody) -> MumbraneProgram:
    """Compile a semantic body into one schema for every active semantic item."""
    units: list[MumbraneUnit] = []
    ports: list[MumbranePort] = []
    coordinates: list[MumbraneCoordinate] = []
    bundles: list[MumbraneVectorBundle] = []
    vectors: list[tuple[float, ...]] = []
    atom_index: dict[str, int] = {}
    full_content_mask = feature_mask("content", "context", "provenance", "geometry", "identity", "region", "integrity")
    relation_mask = feature_mask("operator", "role", "context", "provenance", "geometry", "identity", "region", "integrity")

    def add_bundle(seed: int, geometry: float) -> int:
        indexes = []
        for channel in range(5):
            indexes.append(len(vectors))
            vectors.append(_vector(seed + channel, geometry if channel == 4 else geometry / 2))
        bundles.append(MumbraneVectorBundle(*indexes))
        return len(bundles) - 1

    for atom in body.atoms:
        index = len(units)
        atom_index[atom.atom_id] = index
        coordinate_start = len(coordinates)
        coordinates.extend((
            MumbraneCoordinate(index, AXIS_CODES["scope"], ("global", "fictional", "session", "temporary").index(body.scope) + 1),
            MumbraneCoordinate(index, AXIS_CODES["authority"], 0, 1.0),
            MumbraneCoordinate(index, AXIS_CODES["confidence"], 0, 1.0),
        ))
        bundle_index = add_bundle(index * 31 + 7, .2)
        units.append(MumbraneUnit(
            atom.atom_id, MUMBRANE_SCHEMA, CLASS_CODES["content"], NODE_CODES[atom.kind], full_content_mask,
            len(ports), 0, coordinate_start, 3, bundle_index, 1.0, 0,
            _unit_hash(atom.atom_id, CLASS_CODES["content"], NODE_CODES[atom.kind], full_content_mask),
        ))

    # Context, provenance, identity and region are also MumbraneUnits, rather than special semantic records.
    auxiliary = (("context", "scope"), ("provenance", "provenance_artifact"), ("identity", "entity"), ("region", "scope"), ("region", "scope"))
    for ordinal, (unit_class, kind) in enumerate(auxiliary):
        unit_id = f"{body.body_id}:{unit_class}:{ordinal}"
        index = len(units)
        coordinate_start = len(coordinates)
        coordinates.append(MumbraneCoordinate(index, AXIS_CODES["scope" if unit_class != "identity" else "identity"], ordinal + 1))
        mask = feature_mask(unit_class if unit_class in FEATURE_BITS else "integrity", "integrity")
        units.append(MumbraneUnit(unit_id, MUMBRANE_SCHEMA, CLASS_CODES[unit_class], NODE_CODES[kind], mask, len(ports), 0, coordinate_start, 1, None, 1.0, 0, _unit_hash(unit_id, CLASS_CODES[unit_class], NODE_CODES[kind], mask)))

    for relation in body.relations:
        index = len(units)
        port_start = len(ports)
        ordinal = 0
        for role, atom_ids in relation.role_bindings:
            for atom_id in atom_ids:
                ports.append(MumbranePort(index, ROLE_CODES[role], ordinal, atom_index[atom_id]))
                ordinal += 1
        coordinate_start = len(coordinates)
        coordinates.extend((
            MumbraneCoordinate(index, AXIS_CODES["scope"], ("global", "fictional", "session", "temporary").index(body.scope) + 1),
            MumbraneCoordinate(index, AXIS_CODES["confidence"], 0, relation.base_weight),
            MumbraneCoordinate(index, AXIS_CODES["source"], 1),
        ))
        bundle_index = add_bundle(index * 101 + 13, relation.geometry)
        units.append(MumbraneUnit(
            relation.relation_id, MUMBRANE_SCHEMA, CLASS_CODES["operator"], OPERATOR_CODES[relation.relation_type], relation_mask,
            port_start, len(ports) - port_start, coordinate_start, 3, bundle_index, relation.base_weight, 0,
            _unit_hash(relation.relation_id, CLASS_CODES["operator"], OPERATOR_CODES[relation.relation_type], relation_mask),
        ))
    symbols = tuple(sorted({unit.unit_id for unit in units} | {body.scope}))
    return make_program(tuple(units), tuple(ports), tuple(coordinates), tuple(bundles), tuple(vectors), symbols, ((body.body_id, body.source_text),))


def semantic_signature(body: SemanticBody) -> str:
    return digest({
        "body": body.body_id,
        "atoms": body.atoms,
        "relations": body.relations,
        "scope": body.scope,
        "session": body.session,
    })
