from __future__ import annotations

import torch

from topology_g1.registry import REGISTRY
from topology_g25.assembly import assemble_handoff
from topology_g25.atom_bank import PersistentAtom, PersistentAtomBank
from topology_g25.dataset import generate_kernel_examples, load_kernel_runtime_cases
from topology_g25.field import make_factor
from topology_g25.inference import infer_kernel
from topology_g25.model import TypedAtomKernel
from topology_g25.registry import RELATIONS
from topology_g25.schemas import KernelRuntimeCase


class _Encoder(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.embedding = torch.nn.Embedding(64, 384)
        self.forward_calls = 0

    def tokenize(self, texts: list[str]) -> dict[str, torch.Tensor]:
        length = 12
        return {
            "input_ids": torch.ones((len(texts), length), dtype=torch.long),
            "attention_mask": torch.ones((len(texts), length), dtype=torch.long),
            "offset_mapping": torch.tensor(
                [[[index, index + 1] for index in range(length)] for _ in texts]
            ),
        }

    def forward(
        self, input_ids: torch.Tensor, attention_mask: torch.Tensor, **_: torch.Tensor
    ) -> torch.Tensor:
        self.forward_calls += 1
        return self.embedding(input_ids)


def _accepted(relation: str):
    return next(
        item for item in generate_kernel_examples("train") if item.relation_type == relation
    )


def test_registry_has_every_g1_relation() -> None:
    assert set(RELATIONS) == set(REGISTRY)


def test_one_encoder_forward_per_sentence_request() -> None:
    example = _accepted("implies")
    model = TypedAtomKernel(_Encoder())
    infer_kernel(model, (KernelRuntimeCase(example.source, example.atoms),))
    assert model.encoder.forward_calls == 1


def test_exact_sparse_factor_assembles_through_g1() -> None:
    example = _accepted("implies")
    slots = sum(len(atom_ids) for _, atom_ids in example.role_bindings)
    factor = make_factor(
        source_id=example.source.source_id,
        atoms=example.atoms,
        relation_type="implies",
        role_bindings=example.role_bindings,
        confidence=1.0,
        polarity=example.polarity,
        modality=example.modality,
        scope_id=example.scope_id,
        operator_vector=torch.ones(128),
        role_vectors=torch.ones((slots, 64)),
        binding_vectors=torch.ones((slots, 256)),
        role_scores=tuple(1.0 for _ in range(slots)),
        context_vector=torch.ones(64),
    )
    handoff = assemble_handoff(example.source, example.atoms, (factor,))
    assert handoff is not None
    assert len(handoff.g1_operations) == len(example.atoms) + 1


def test_runtime_loader_rejects_gold_path(tmp_path) -> None:
    forbidden = tmp_path / "gold" / "kernel-inputs.jsonl"
    forbidden.parent.mkdir()
    forbidden.write_text("", encoding="utf-8")
    try:
        load_kernel_runtime_cases(forbidden)
    except PermissionError:
        pass
    else:
        raise AssertionError("runtime accepted a gold path")


def test_persistent_atom_matching_is_typed_and_bounded() -> None:
    example = _accepted("implies")
    occurrence = example.atoms[0]
    bank = PersistentAtomBank(
        (
            PersistentAtom(
                "persistent:correct",
                occurrence.text,
                occurrence.node_kind,
                "global",
                example.source.session_id,
                None,
                None,
                occurrence.canonical_vector,
            ),
            PersistentAtom(
                "persistent:wrong-scope",
                occurrence.text,
                occurrence.node_kind,
                "fictional",
                example.source.session_id,
                None,
                None,
                occurrence.canonical_vector,
            ),
        )
    )
    match = bank.resolve(occurrence, session_id=example.source.session_id)
    assert match.disposition == "existing"
    assert match.candidate_object_ids == ("persistent:correct",)
    assert match.postings_visited <= 32
