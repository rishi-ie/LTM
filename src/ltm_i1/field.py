from __future__ import annotations

import hashlib
import math
from dataclasses import replace
from pathlib import Path

from ltm.adapters import from_g1
from ltm.codec import pack_program
from ltm.schema import FieldProgramV2, SourceArchive, SurfaceClaimRecord, VectorRef, VectorSpaceSpec
from topology_field_ir.codec import write_vector_sidecar

from .schemas import IntegrationCase


def _unit(seed: str, dimension: int) -> tuple[float, ...]:
    values = []
    for index in range(dimension):
        digest = hashlib.sha256(f"{seed}:{index}".encode()).digest()
        values.append((int.from_bytes(digest[:4], "little") / 2**32) * 2.0 - 1.0)
    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return tuple(value / norm for value in values)


def _config():
    from ltm.adapters import config_from_g1
    zero = "0" * 64
    spaces = tuple(VectorSpaceSpec(name, "i1", zero, dimension) for name, dimension in (("content", 384), ("operator", 128), ("role", 64), ("context", 64), ("binding", 256)))
    return config_from_g1(vector_spaces=spaces)


def build_field(case: IntegrationCase, root: Path) -> tuple[FieldProgramV2, SourceArchive]:
    program, archive = from_g1(case.nodes, (case.relation,), _config())
    claims = tuple(SurfaceClaimRecord(atom.atom_id, f"entity-{index}", "is", f"object-{index}") for index, atom in enumerate(program.atoms))
    archive = replace(archive, surface_claims=claims)
    refs: list[VectorRef] = []
    sidecar_rows: dict[str, list[tuple[float, ...]]] = {name: [] for name in ("content", "operator", "role", "context", "binding")}

    def add(space: str, values: tuple[float, ...]) -> int:
        row = len(sidecar_rows[space]); sidecar_rows[space].append(values)
        return len(refs) + row  # temporary, corrected after rows are materialized

    # We collect logical references first, then assign the global row index.
    logical: list[tuple[str, int, str]] = []
    def collect(space: str, values: tuple[float, ...], label: str) -> int:
        row = len(sidecar_rows[space]); sidecar_rows[space].append(values); logical.append((space, row, label)); return len(logical) - 1

    atom_refs: list[tuple[int, int]] = []
    for index, _atom in enumerate(program.atoms):
        atom_refs.append((collect("content", _unit(f"{case.case_id}:a:{index}", 384), f"content:{index}:canonical"), collect("content", _unit(f"{case.case_id}:o:{index}", 384), f"content:{index}:occurrence")))
    factor_ref = collect("operator", _unit(f"{case.case_id}:operator", 128), "operator:0")
    context_ref = collect("context", _unit(f"{case.case_id}:context", 64), "context:0")
    role_refs = [collect("role", _unit(f"{case.case_id}:role:{index}", 64), f"role:{index}") for index, _ in enumerate(program.bindings)]
    binding_refs = [collect("binding", _unit(f"{case.case_id}:binding:{index}", 256), f"binding:{index}") for index, _ in enumerate(program.bindings)]

    sidecar_meta: dict[str, tuple[str, tuple[str, ...]]] = {}
    for space, rows in sidecar_rows.items():
        sidecar_meta[space] = write_vector_sidecar(root / f"{space}.ltmf", rows, len(rows[0]) if rows else next(item.dimension for item in program.config.vector_spaces if item.space_id == space))
    by_logical: dict[int, int] = {}
    for global_index, (space, row, label) in enumerate(logical):
        side_hash, row_hashes = sidecar_meta[space]
        refs.append(VectorRef(label, space, side_hash, row, row_hashes[row]))
        by_logical[logical.index((space, row, label))] = global_index
    atoms = tuple(replace(atom, canonical_vector=by_logical[atom_refs[index][0]], occurrence_vector=by_logical[atom_refs[index][1]]) for index, atom in enumerate(program.atoms))
    factors = tuple(replace(program.factors[0], operator_vector=by_logical[factor_ref], context_index=len(program.contexts)) for _ in (0,))
    contexts = program.contexts + (replace(program.contexts[program.factors[0].context_index], vector_ref=by_logical[context_ref]),)
    bindings = tuple(replace(item, role_vector=by_logical[role_refs[index]], binding_vector=by_logical[binding_refs[index]]) for index, item in enumerate(program.bindings))
    program = replace(program, atoms=atoms, factors=factors, contexts=contexts, bindings=bindings, vectors=tuple(refs))
    pack_program(root, program, archive)
    return program, archive

