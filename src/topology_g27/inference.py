"""Gold-free coordinate inference and atomic FieldIR compilation."""

from __future__ import annotations

import hashlib
import re
import time

from topology_field_ir import GoldenAtom

from .field import build_program
from .kernel import CoordinateKernel
from .schemas import RuntimeExample, SentenceCompilation


def _extract_public_atoms(item: RuntimeExample) -> tuple[GoldenAtom, ...]:
    if item.atoms:
        return item.atoms
    values = []
    for index, match in enumerate(re.finditer(r"\b(?P<kind>[a-z_]+)_(?P<id>[A-Z]\d{5}_\d+)\b", item.text)):
        value = match.group(0)
        kind = match.group("kind")
        values.append(GoldenAtom(f"a{index + 1}", kind, value, value, item.source_id, match.start(), match.end(), item.context, hashlib.sha256(item.text.encode()).hexdigest()))
    return tuple(values)


def compile_example(kernel: CoordinateKernel, item: RuntimeExample) -> SentenceCompilation:
    started = time.perf_counter()
    atoms = _extract_public_atoms(item)
    state = kernel.score(item.text, atoms)
    graph = state.candidates[0]
    program = None
    failure = []
    if graph.disposition == "accept":
        try:
            program = build_program(item.source_id, atoms, graph, atoms[0].provenance_sha256 if atoms else "0" * 64, state.coordinate.activations)
        except (ValueError, KeyError) as exc:
            failure.append(type(exc).__name__)
            graph = type(graph)(graph.relation_type, graph.role_bindings, graph.relation_set, graph.context, graph.score, graph.probability, graph.margin, "quarantine")
            state = type(state)(state.source_id, state.atoms, state.coordinate, state.bindings, (graph,))
    disposition = graph.disposition if program is not None or graph.disposition != "accept" else "quarantine"
    return SentenceCompilation(item.source_id, state, program, disposition, tuple(failure), (time.perf_counter() - started) * 1000)


def infer(kernel: CoordinateKernel, examples: tuple[RuntimeExample, ...]) -> tuple[SentenceCompilation, ...]:
    kernel.eval()
    return tuple(compile_example(kernel, item) for item in examples)
