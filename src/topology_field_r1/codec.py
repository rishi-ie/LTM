"""Text-free numeric FieldIR conversion used by the representation audit."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from topology_field_ir.schemas import FieldContext, FieldProgram, GoldenAtom, TypedFactor, VectorRef
from topology_g1.registry import REGISTRY
from topology_g1.schemas import (
    NodeKind,
    Provenance,
    RelationInstance,
    RoleBinding,
    TopologyNode,
    ValidityInterval,
)

from .schemas import (
    NumericAtom,
    NumericBinding,
    NumericContext,
    NumericFactor,
    NumericFieldProgram,
    NumericProvenance,
    NumericVectorRef,
    SourceArchive,
)

MAGIC = "ltmf/2"
_NONE = 0xFFFFFFFF
_POLARITY = {"positive": 1, "negative": 2}
_NODE_KINDS = tuple(sorted(item.value for item in NodeKind))
_KIND_CODES = {name: index + 1 for index, name in enumerate(_NODE_KINDS)}
_RELATIONS = tuple(sorted(REGISTRY))
_OPERATOR_CODES = {name: index + 1 for index, name in enumerate(_RELATIONS)}
_ROLES = tuple(sorted({role.name for spec in REGISTRY.values() for role in spec.roles}))
_ROLE_CODES = {name: index + 1 for index, name in enumerate(_ROLES)}


def _key(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _index(values: list[str], value: str) -> int:
    try:
        return values.index(_key(value))
    except ValueError:
        values.append(_key(value))
        return len(values) - 1


def _vector(ref: VectorRef | None, values: list[NumericVectorRef], archive: list[tuple[str, str]], spaces: list[str]) -> int | None:
    if ref is None:
        return None
    key = _key(ref.vector_id)
    for index, item in enumerate(values):
        if item.vector_key == int(key[:16], 16):
            return index
    space_key = _index(spaces, ref.space_id)
    archive.append((key, ref.vector_id))
    values.append(NumericVectorRef(int(key[:16], 16), space_key, ref.sidecar_sha256, ref.row_index, ref.row_sha256))
    return len(values) - 1


def from_fieldir(program: FieldProgram) -> tuple[NumericFieldProgram, SourceArchive]:
    """Convert a FieldIR program without placing text in the active structure."""
    ids: list[str] = []
    id_values: dict[str, str] = {}
    modalities: list[str] = []
    spaces: list[str] = []
    vectors: list[NumericVectorRef] = []
    vector_archive: list[tuple[str, str]] = []
    contexts: list[NumericContext] = []
    context_map: dict[FieldContext, int] = {}
    provenances: list[NumericProvenance] = []
    provenance_map: dict[tuple[str, int, int, str], int] = {}

    def id_index(value: str) -> int:
        digest = _key(value)
        id_values[digest] = value
        if digest not in ids:
            ids.append(digest)
        return ids.index(digest)

    def context_index(value: FieldContext) -> int:
        if value in context_map:
            return context_map[value]
        if value.modality not in modalities:
            modalities.append(value.modality)
        modality_key = modalities.index(value.modality)
        result = NumericContext(
            id_index(value.scope_id),
            _POLARITY[value.polarity],
            modality_key,
            value.valid_from,
            value.valid_to,
            value.confidence,
            value.authority,
            value.priority,
        )
        contexts.append(result); context_map[value] = len(contexts) - 1
        return len(contexts) - 1

    def provenance_index(source_id: str, start: int, end: int, digest: str) -> int:
        key = (source_id, start, end, digest)
        if key not in provenance_map:
            provenance_map[key] = len(provenances)
            provenances.append(NumericProvenance(id_index(source_id), start, end, digest))
        return provenance_map[key]

    atoms: list[NumericAtom] = []
    atom_index: dict[str, int] = {}
    text: list[tuple[str, str, str]] = []
    for atom in program.atoms:
        id_index(atom.atom_id)
        atom_index[atom.atom_id] = len(atoms)
        atom_digest = _key(atom.atom_id)
        text.append((atom_digest, atom.canonical_text, atom.occurrence_text))
        atoms.append(NumericAtom(
            int(atom_digest[:16], 16),
            _KIND_CODES[atom.kind],
            context_index(atom.context),
            provenance_index(atom.source_id, atom.source_start, atom.source_end, atom.provenance_sha256),
            id_index(atom.source_id), atom.source_start, atom.source_end,
            _vector(atom.canonical_vector, vectors, vector_archive, spaces),
            _vector(atom.occurrence_vector, vectors, vector_archive, spaces),
        ))
    bindings: list[NumericBinding] = []
    factors: list[NumericFactor] = []
    factor_keys: list[str] = []
    for factor in program.factors:
        id_index(factor.factor_id)
        start = len(bindings); factor_index = len(factors)
        role_refs = iter(factor.role_vectors)
        binding_refs = iter(factor.binding_vectors)
        ordinal = 0
        for role, atom_ids in factor.role_bindings:
            for atom_id in atom_ids:
                bindings.append(NumericBinding(
                    factor_index, _ROLE_CODES[role], ordinal, atom_index[atom_id],
                    _vector(next(role_refs, None), vectors, vector_archive, spaces),
                    _vector(next(binding_refs, None), vectors, vector_archive, spaces),
                ))
                ordinal += 1
        factor_digest = _key(factor.factor_id); factor_keys.append(factor_digest)
        factors.append(NumericFactor(
            int(factor_digest[:16], 16), _OPERATOR_CODES[factor.relation_type], context_index(factor.context),
            provenance_index("fieldir", 0, 0, factor.provenance_sha256), start, len(bindings) - start,
            factor.base_weight, _vector(factor.operator_vector, vectors, vector_archive, spaces),
        ))
    numeric = NumericFieldProgram(
        int(_key(program.program_id)[:16], 16), program.registry_sha256,
        tuple(_key(atom.atom_id) for atom in program.atoms), tuple(factor_keys), tuple(ids), tuple(spaces),
        tuple(atoms), tuple(factors), tuple(bindings), tuple(contexts), tuple(provenances), tuple(vectors),
    )
    archive = SourceArchive(
        program.program_id, tuple(text),
        tuple((key, id_values[key]) for key in ids),
        tuple((_key(value), value) for value in modalities), tuple(vector_archive),
        tuple((_key(space.space_id), asdict(space)) for space in program.vector_spaces),
    )
    return numeric, archive


def _archive_map(rows: tuple[tuple[str, str], ...]) -> dict[str, str]:
    return dict(rows)


def _context(item: NumericContext, archive: SourceArchive, ids: tuple[str, ...]) -> FieldContext:
    id_map = _archive_map(archive.ids); modality_map = _archive_map(archive.modalities)
    return FieldContext(
        id_map[ids[item.scope_key]], {1: "positive", 2: "negative"}[item.polarity_code],
        modality_map[archive.modalities[item.modality_key][0]],
        item.valid_from, item.valid_to, item.confidence, item.authority, item.priority,
    )


def to_fieldir(numeric: NumericFieldProgram, archive: SourceArchive) -> FieldProgram:
    """Legacy reconstruction only; text comes from the non-active archive."""
    text = {key: (canonical, occurrence) for key, canonical, occurrence in archive.atom_text}
    ids = _archive_map(archive.ids); vectors = {key: value for key, value in archive.vector_ids}
    space_ids = {key: value["space_id"] for key, value in archive.vector_spaces}
    spaces = tuple(__import__("topology_field_ir.schemas", fromlist=["VectorSpaceSpec"]).VectorSpaceSpec(**value) for _key_value, value in archive.vector_spaces)
    contexts = tuple(_context(item, archive, numeric.id_keys) for item in numeric.contexts)

    def vector(index: int | None) -> VectorRef | None:
        if index is None:
            return None
        item = numeric.vectors[index]
        return VectorRef(vectors[f"{item.vector_key:016x}" if f"{item.vector_key:016x}" in vectors else next(key for key in vectors if int(key[:16], 16) == item.vector_key)], space_ids[numeric.vector_space_keys[item.space_key]], item.sidecar_sha256, item.row_index, item.row_sha256)

    atoms: list[GoldenAtom] = []
    atom_ids: list[str] = []
    for index, item in enumerate(numeric.atoms):
        key = numeric.atom_keys[index]; atom_id = ids[key]
        atom_ids.append(atom_id)
        canonical, occurrence = text[key]
        provenance = numeric.provenances[item.provenance_index]
        atoms.append(GoldenAtom(atom_id, _NODE_KINDS[item.kind_code - 1], canonical, occurrence, ids[numeric.id_keys[item.source_key]], item.source_start, item.source_end, contexts[item.context_index], provenance.source_sha256, vector(item.canonical_vector), vector(item.occurrence_vector)))
    factors: list[TypedFactor] = []
    for index, item in enumerate(numeric.factors):
        selected = numeric.bindings[item.binding_start:item.binding_start + item.binding_count]
        grouped: dict[str, list[str]] = {}
        role_vectors: list[VectorRef] = []; binding_vectors: list[VectorRef] = []
        for binding in selected:
            role = _ROLES[binding.role_code - 1]; grouped.setdefault(role, []).append(atom_ids[binding.atom_index])
            if binding.role_vector is not None: role_vectors.append(vector(binding.role_vector))
            if binding.binding_vector is not None: binding_vectors.append(vector(binding.binding_vector))
        provenance = numeric.provenances[item.provenance_index]
        factor_id = ids[numeric.factor_keys[index]]
        factors.append(TypedFactor(factor_id, _RELATIONS[item.operator_code - 1], tuple((key, tuple(value)) for key, value in grouped.items()), contexts[item.context_index], provenance.source_sha256, item.base_weight, vector(item.operator_vector), tuple(role_vectors), tuple(binding_vectors)))
    return FieldProgram(archive.program_id, numeric.registry_sha256, spaces, tuple(atoms), tuple(factors))


def numeric_digest(program: NumericFieldProgram) -> str:
    payload = {"magic": MAGIC, "registry": program.registry_sha256, "atoms": [asdict(item) for item in program.atoms], "factors": [asdict(item) for item in program.factors], "bindings": [asdict(item) for item in program.bindings], "contexts": [asdict(item) for item in program.contexts], "provenances": [asdict(item) for item in program.provenances], "vectors": [asdict(item) for item in program.vectors]}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def active_bytes(program: NumericFieldProgram) -> int:
    """Deterministic packed-layout accounting; archive text is intentionally excluded."""
    return (
        96
        + len(program.id_keys) * 32
        + len(program.vector_space_keys) * 32
        + len(program.atom_keys) * 32
        + len(program.factor_keys) * 32
        + len(program.atoms) * 40
        + len(program.factors) * 40
        + len(program.bindings) * 24
        + len(program.contexts) * 40
        + len(program.provenances) * 48
        + len(program.vectors) * 80
    )


def write_program(path: Path, program: NumericFieldProgram, archive: SourceArchive) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # ponytail: JSON is the audit transport; production packing follows only after compatibility passes.
    path.write_text(json.dumps(asdict(program), sort_keys=True, separators=(",", ":")))
    path.with_suffix(path.suffix + ".archive.json").write_text(json.dumps(asdict(archive), sort_keys=True, separators=(",", ":")))


def read_program(path: Path) -> tuple[NumericFieldProgram, SourceArchive]:
    program = json.loads(path.read_text())
    archive = json.loads(path.with_suffix(path.suffix + ".archive.json").read_text())
    return NumericFieldProgram(
        **{**program, "atom_keys": tuple(program["atom_keys"]), "factor_keys": tuple(program["factor_keys"]), "id_keys": tuple(program["id_keys"]), "vector_space_keys": tuple(program["vector_space_keys"]), "atoms": tuple(NumericAtom(**item) for item in program["atoms"]), "factors": tuple(NumericFactor(**item) for item in program["factors"]), "bindings": tuple(NumericBinding(**item) for item in program["bindings"]), "contexts": tuple(NumericContext(**item) for item in program["contexts"]), "provenances": tuple(NumericProvenance(**item) for item in program["provenances"]), "vectors": tuple(NumericVectorRef(**item) for item in program["vectors"])}
    ), SourceArchive(**{key: tuple(tuple(item) for item in value) if isinstance(value, list) else value for key, value in archive.items()})


def text_free_g1(program: NumericFieldProgram) -> tuple[tuple[TopologyNode, ...], tuple[RelationInstance, ...]]:
    """Core execution view: no archive or atom text is consulted."""
    def scope(context: NumericContext) -> str:
        key = program.id_keys[context.scope_key]
        return "global" if key == _key("global") else f"scope:{key}"

    nodes = tuple(TopologyNode(program.atom_keys[index], 2, NodeKind(_NODE_KINDS[item.kind_code - 1]), (), scope(program.contexts[item.context_index]), ValidityInterval(program.contexts[item.context_index].valid_from, program.contexts[item.context_index].valid_to), (Provenance(f"source:{item.source_key}", item.source_start, item.source_end, program.provenances[item.provenance_index].source_sha256),)) for index, item in enumerate(program.atoms))
    by_index = {index: node for index, node in enumerate(nodes)}
    relations = []
    for index, factor in enumerate(program.factors):
        selected = program.bindings[factor.binding_start:factor.binding_start + factor.binding_count]
        arguments = tuple(RoleBinding(_ROLES[item.role_code - 1], by_index[item.atom_index].node_id) for item in selected)
        relations.append(RelationInstance(program.factor_keys[index], 2, _RELATIONS[factor.operator_code - 1], arguments, scope(program.contexts[factor.context_index]), ValidityInterval(program.contexts[factor.context_index].valid_from, program.contexts[factor.context_index].valid_to), program.contexts[factor.context_index].confidence, program.contexts[factor.context_index].authority, (Provenance("numeric", 0, 0, program.provenances[factor.provenance_index].source_sha256),)))
    return nodes, tuple(relations)
