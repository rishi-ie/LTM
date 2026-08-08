"""Constrained conversion from model outputs to atom programs."""

from __future__ import annotations

import time

import torch

from topology_g1.registry import REGISTRY

from .compiler import DISPOSITIONS, AtomTopologyCompiler
from .program import assemble_program
from .registry import NODE_KINDS, RELATION_LABELS
from .schemas import (
    AtomMatch,
    GroundedAtom,
    OperatorHypothesis,
    ProgramExample,
    SentenceCompilationResult,
    TopologyProgram,
)
from .vectors import normalized_hash_vector


def _offset_span(offsets: torch.Tensor, start_token: int, end_token: int, source: str) -> tuple[int, int] | None:
    start = tuple(int(value) for value in offsets[start_token])
    end = tuple(int(value) for value in offsets[end_token])
    if start[1] <= start[0] or end[1] <= end[0]:
        return None
    begin, finish = start[0], end[1]
    if finish <= begin or finish > len(source):
        return None
    return begin, finish


@torch.no_grad()
def compile_examples(model: AtomTopologyCompiler, examples: tuple[ProgramExample, ...], *, batch_size: int = 8) -> tuple[SentenceCompilationResult, ...]:
    values: list[SentenceCompilationResult] = []
    model.eval()
    for index in range(0, len(examples), batch_size):
        batch = examples[index : index + batch_size]
        tokens = model.encoder.tokenize([item.source.text for item in batch])
        offsets = tokens["offset_mapping"]
        decoded = model.decode(tokens)
        for row, (example, prediction) in enumerate(zip(batch, decoded)):
            started = time.perf_counter()
            disposition = DISPOSITIONS[prediction.disposition]
            # A statement cannot be accepted until every selected atom maps to a real source span.
            atoms: list[GroundedAtom] = []
            if disposition == "accept":
                relation = RELATION_LABELS[prediction.relation]
                required_atoms = sum(role.minimum for role in REGISTRY[relation].roles)
                # Candidate construction binds the first ordered slots.  Only
                # these slots may participate in a selected legal graph; noisy
                # unused slots cannot turn into invented operations.
                for slot in range(required_atoms):
                    span = _offset_span(offsets[row], prediction.starts[slot], prediction.ends[slot], example.source.text)
                    if span is None:
                        continue
                    begin, end = span
                    text = example.source.text[begin:end]
                    atoms.append(
                        GroundedAtom(
                            f"slot-{slot}", NODE_KINDS[prediction.kinds[slot]], text, begin, end,
                            tuple(float(value) for value in normalized_hash_vector(text)),
                            tuple(float(value) for value in normalized_hash_vector(text, 128)),
                            "global", None, None, "positive", "asserted", prediction.confidence,
                        )
                    )
            operators: tuple[OperatorHypothesis, ...] = ()
            if disposition == "accept":
                spec = REGISTRY[relation]
                cursor = 0
                bindings: list[tuple[str, tuple[str, ...]]] = []
                compatible = True
                for role in spec.roles:
                    ids: list[str] = []
                    for _ in range(role.minimum):
                        if cursor >= len(atoms) or atoms[cursor].node_kind not in {kind.value for kind in role.allowed_kinds}:
                            compatible = False
                            break
                        ids.append(atoms[cursor].local_id)
                        cursor += 1
                    bindings.append((role.name, tuple(ids)))
                if compatible and cursor <= len(atoms):
                    operators = (OperatorHypothesis("predicted-relation", relation, tuple(bindings), "global", None, None, prediction.confidence),)
                else:
                    disposition = "clarification_required"
            program = TopologyProgram(
                example.source.source_id,
                tuple(atoms),
                tuple(AtomMatch(atom.local_id, (), "new", prediction.confidence, prediction.confidence) for atom in atoms),
                operators,
                disposition,
                prediction.confidence,
                prediction.confidence,
            )
            accepted = assemble_program(example.source, program)
            if disposition == "accept" and accepted is None:
                disposition = "quarantine"
                program = TopologyProgram(example.source.source_id, (), (), (), disposition, prediction.confidence, prediction.confidence)
            values.append(
                SentenceCompilationResult(
                    example.source.source_id,
                    (program,),
                    accepted,
                    disposition,
                    () if accepted is not None or disposition != "accept" else ("G1_VALIDATION",),
                    (time.perf_counter() - started) * 1000,
                    int(tokens["attention_mask"][row].sum()),
                )
            )
    return tuple(values)
