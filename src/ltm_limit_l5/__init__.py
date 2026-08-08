"""L5 compiled multi-hypothesis latent field equilibrium."""

from typing import TYPE_CHECKING, Any

from .schemas import CompiledPromptField, FieldEquilibriumResult, LatentModeState

if TYPE_CHECKING:
    from .lifecycle import L5Lifecycle


def __getattr__(name: str) -> Any:
    if name == "L5Lifecycle":
        from .lifecycle import L5Lifecycle

        return L5Lifecycle
    raise AttributeError(name)

__all__ = ("CompiledPromptField", "FieldEquilibriumResult", "L5Lifecycle", "LatentModeState")
