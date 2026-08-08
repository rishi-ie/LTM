"""Inference ablations used to verify that G2.6 is testing pair structure."""

from __future__ import annotations

from .inference import infer_examples

ABLATIONS = {
    "full": {},
    "no_registry_prototype": {"registry": True},
    "no_ordered_pair": {"pairs": True},
    "no_role_binding": {"roles": True},
    "no_context": {"context": True},
    "no_reconciliation": {"cycles": 0},
}


def run_ablation(model, encoder, examples, name: str):
    flags = ABLATIONS.get(name, {})
    return infer_examples(model, encoder, examples, ablation=flags)

