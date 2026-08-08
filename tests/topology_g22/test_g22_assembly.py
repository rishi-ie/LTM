from dataclasses import replace

from topology_g22.assemble import assemble
from topology_g22.dataset import generate_sentence_examples
from topology_g22.schemas import SentenceFragment, StructuredRelationCandidate


def _accepted_fragment() -> SentenceFragment:
    example = next(item for item in generate_sentence_examples("development") if item.gold.disposition == "accept")
    gold = example.gold
    return SentenceFragment(gold.source, "accept", gold.spans, gold.relations, None, None, "round-trip", 1.0)


def test_valid_fragment_is_atomically_assembled_and_has_field_handoff() -> None:
    assembled = assemble(_accepted_fragment())
    assert assembled is not None
    assert assembled.delta.relation_ids
    assert assembled.handoff.factor_ids == assembled.delta.relation_ids


def test_invalid_relation_never_creates_partial_delta() -> None:
    fragment = _accepted_fragment()
    invalid = StructuredRelationCandidate("not_registered", fragment.relations[0].role_local_ids, "arg1_to_arg2", "global", None, None, 1.0, 1.0)
    assert assemble(replace(fragment, relations=(invalid,))) is None
