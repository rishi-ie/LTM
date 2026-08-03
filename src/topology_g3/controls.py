from __future__ import annotations

from .resolver import resolve


def run_controls(signature, indexes):
    return {mode: resolve(signature, indexes, mode) for mode in ("full", "lexical", "semantic")}
