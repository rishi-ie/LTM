"""Reuse the pinned one-pass MiniLM implementation."""

from topology_g211.encoder import EXPECTED_HASHES, MODEL_PATH, OnePassMiniLM, assert_model_hashes

__all__ = ("EXPECTED_HASHES", "MODEL_PATH", "OnePassMiniLM", "assert_model_hashes")
