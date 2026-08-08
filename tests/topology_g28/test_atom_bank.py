from topology_g28.atom_bank import ATOM_BANK_V1, ATOM_BANK_V11, RELATIONS


def test_atom_bank_derives_all_g1_relations_once() -> None:
    assert len(RELATIONS) == 18
    assert {item.relation_type for item in ATOM_BANK_V1.operators} == set(RELATIONS)
    assert ATOM_BANK_V1.bank_hash != ATOM_BANK_V11.bank_hash


def test_v11_changes_only_declared_operator_policy() -> None:
    v1 = {item.relation_type: item for item in ATOM_BANK_V1.operators}
    v11 = {item.relation_type: item for item in ATOM_BANK_V11.operators}
    assert v1["causes_hypothetically"].base_field_weight == 1.0
    assert v11["causes_hypothetically"].base_field_weight == .75
    assert "fact" in v11["supports"].roles[0].allowed_node_kinds
