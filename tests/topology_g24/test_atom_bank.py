from topology_g24.atom_bank import build_atom_bank
from topology_g24.schemas import GroundedAtom, MemoryAtom
from topology_g24.vectors import normalized_hash_vector


def _memory(object_id: str, text: str, *, scope: str = "global", session: str | None = None) -> MemoryAtom:
    return MemoryAtom(
        object_id,
        "claim",
        text,
        (),
        normalized_hash_vector(text),
        scope,
        None,
        None,
        session,
        ("source",),
        "a" * 64,
    )


def _grounded(text: str, *, scope: str = "global") -> GroundedAtom:
    return GroundedAtom(
        "local",
        "claim",
        text,
        0,
        len(text),
        normalized_hash_vector(text),
        normalized_hash_vector(text, 128),
        scope,
        None,
        None,
        "positive",
        "asserted",
        1.0,
    )


def test_atom_bank_resolves_existing_atom_without_scanning_incompatible_scope():
    bank = build_atom_bank(
        (
            _memory("global", "Pevin has the beryl seal"),
            _memory("fictional", "Pevin has the beryl seal", scope="fictional"),
        ),
        clusters=2,
    )

    match = bank.resolve(_grounded("Pevin has the beryl seal"), session_id="session-a")

    assert match.disposition == "existing"
    assert match.target_object_ids == ("global",)


def test_atom_bank_marks_near_equal_candidates_ambiguous():
    bank = build_atom_bank(
        (_memory("first", "Pevin has the beryl seal"), _memory("second", "Pevin has the beryl seal")),
        clusters=2,
    )

    match = bank.resolve(_grounded("Pevin has the beryl seal"), session_id=None)

    assert match.disposition == "ambiguous"
    assert set(match.target_object_ids) == {"first", "second"}
