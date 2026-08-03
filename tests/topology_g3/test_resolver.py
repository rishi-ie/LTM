from topology_g3.generator import build_prompts, build_topology
from topology_g3.indexes import Indexes
from topology_g3.resolver import resolve, signature_from_dict


def test_canonical_address_resolves():
    topology = build_topology(1731); inputs, _ = build_prompts(topology, 1732, 20)
    record = next(row for row in inputs if row["category"] == "canonical")
    result = resolve(signature_from_dict(record["signature"]), Indexes(topology))
    assert result.disposition == "resolved"
    assert result.complete_scan is False

def test_ambiguous_alias_is_not_forced():
    topology = build_topology(1731); inputs, _ = build_prompts(topology, 1732, 20)
    record = next(row for row in inputs if row["category"] == "ambiguous")
    result = resolve(signature_from_dict(record["signature"]), Indexes(topology))
    assert result.disposition == "clarification_required"
