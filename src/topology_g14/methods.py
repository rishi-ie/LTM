from __future__ import annotations

from .schemas import MethodSpec

METHODS = (
    MethodSpec("full_controlled_ltm", "structured", "typed-address", "G6+G7", "G11", "G9"),
    MethodSpec("exhaustive_oracle", "gold-structured", "exhaustive", "G6", "G11", "independent"),
    MethodSpec("hybrid_rag", "structured", "bounded evidence retrieval", "exact on retrieved evidence", "history-slice", "none"),
    MethodSpec("summary_qwen", "structured", "extractive summary", "exact on summary evidence", "summary", "none"),
    MethodSpec("no_exact_propagation", "structured", "typed-address", "none", "G11", "G9"),
    MethodSpec("no_soft_optimization", "structured", "typed-address", "G6", "G11", "G9"),
    MethodSpec("no_session_overlay", "structured", "typed-address", "G6+G7", "none", "G9"),
    MethodSpec("no_coverage", "structured", "fixed-frontier", "G6+G7", "G11", "G9"),
    MethodSpec("no_verifier", "structured", "typed-address", "G6+G7", "G11", "none"),
)
