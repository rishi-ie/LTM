"""Versioned, vector-routed typed field intermediate representation."""

from .adapters import OptimizationCapability, capability
from .codec import (
    artifact_digest,
    canonical_json,
    read_vector_sidecar,
    semantic_digest,
    verify_vector_artifacts,
    write_vector_sidecar,
)
from .schemas import (
    FieldContext,
    FieldProgram,
    GoldenAtom,
    TypedFactor,
    VectorRef,
    VectorSpaceSpec,
)
from .validate import FieldIRValidationError, to_g1, validate_program

__all__ = (
    "FieldContext",
    "FieldIRValidationError",
    "FieldProgram",
    "GoldenAtom",
    "OptimizationCapability",
    "TypedFactor",
    "VectorRef",
    "VectorSpaceSpec",
    "artifact_digest",
    "canonical_json",
    "capability",
    "read_vector_sidecar",
    "semantic_digest",
    "to_g1",
    "validate_program",
    "verify_vector_artifacts",
    "write_vector_sidecar",
)
