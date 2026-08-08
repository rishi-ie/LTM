"""Deterministic atomic-coordinate composition."""

from __future__ import annotations

from .basis import coordinates_for_relation, relation_from_coordinates
from .schemas import AtomicCoordinate, AtomicFieldPatch


def compose_relation(source_id: str, relation: str, *, residual: tuple[float, ...] = ()) -> AtomicFieldPatch:
    coordinates = coordinates_for_relation(relation)
    recovered = relation_from_coordinates(coordinates)
    if recovered != relation:
        raise ValueError("ATOMIC_COMPOSITION_MISMATCH")
    return AtomicFieldPatch(source_id, coordinates, (recovered,), residual, "accept")


def compose_coordinates(source_id: str, coordinates: tuple[AtomicCoordinate, ...], *, residual: tuple[float, ...] = ()) -> AtomicFieldPatch:
    relation = relation_from_coordinates(coordinates)
    return AtomicFieldPatch(source_id, coordinates, (relation,), residual, "accept")

