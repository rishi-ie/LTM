from topology_g1.registry import REGISTRY
from topology_g29.atom_bank import ATOM_BANK_V1, ATOM_BANK_V11


def test_atom_bank_is_complete_and_registry_derived() -> None:
    assert tuple(item.relation_type for item in ATOM_BANK_V1.operators) == tuple(REGISTRY)
    assert len(ATOM_BANK_V1.operators) == 18
    assert ATOM_BANK_V1.bank_hash != ATOM_BANK_V11.bank_hash
    assert all(item.roles for item in ATOM_BANK_V1.operators)
