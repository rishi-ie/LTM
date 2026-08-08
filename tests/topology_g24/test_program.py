from topology_g24.program import assemble_program, program_signature, tensor_signature
from topology_g24.schemas import (
    GroundedAtom,
    OperatorHypothesis,
    SentenceSource,
    TopologyProgram,
    sha256_text,
)
from topology_g24.vectors import normalized_hash_vector


def _source() -> SentenceSource:
    text = "If Pevin has the beryl seal, Laskor may enter."
    return SentenceSource("source-1", "doc-1", "session-1", 0, text, 0, len(text), sha256_text(text))


def _atom(local_id: str, text: str, start: int, end: int) -> GroundedAtom:
    return GroundedAtom(
        local_id,
        "claim",
        text,
        start,
        end,
        normalized_hash_vector(text),
        normalized_hash_vector(text, 128),
        "global",
        None,
        None,
        "positive",
        "asserted",
        1.0,
    )


def test_program_assembles_losslessly_through_g1_and_tensor_ir():
    source = _source()
    premise = _atom("a1", "Pevin has the beryl seal", 3, 28)
    conclusion = _atom("a2", "Laskor may enter", 30, 47)
    operator = OperatorHypothesis(
        "r1",
        "implies",
        (("premise", ("a1",)), ("conclusion", ("a2",))),
        "global",
        None,
        None,
        1.0,
    )
    program = TopologyProgram(source.source_id, (premise, conclusion), (), (operator,), "accept", 1.0, 1.0)

    value = assemble_program(source, program)

    assert value is not None
    assert len(value.g1_nodes) == 2
    assert value.g1_relations[0].relation_type == "implies"
    assert tensor_signature(value.tensor_ir)[0] == tuple(
        sorted((atom.node_kind, atom.source_start, atom.source_end, atom.text, atom.scope_id) for atom in program.atoms)
    )
    assert program_signature(program)[0] == "accept"


def test_illegal_role_type_is_rejected_atomically():
    source = _source()
    entity = GroundedAtom(
        "entity",
        "entity",
        "Pevin",
        3,
        8,
        normalized_hash_vector("Pevin"),
        normalized_hash_vector("Pevin", 128),
        "global",
        None,
        None,
        "positive",
        "asserted",
        1.0,
    )
    claim = _atom("claim", "Laskor may enter", 30, 47)
    operator = OperatorHypothesis(
        "bad",
        "implies",
        (("premise", ("entity",)), ("conclusion", ("claim",))),
        "global",
        None,
        None,
        1.0,
    )
    program = TopologyProgram(source.source_id, (entity, claim), (), (operator,), "accept", 1.0, 1.0)

    assert assemble_program(source, program) is None
