"""Exact formal-expression to Mumbrane IR v1 projection."""

from __future__ import annotations

import hashlib

from ltm_inference_i3.schemas import FormalExpression
from ltm_r2.codebook import AXIS_CODES, CLASS_CODES, FEATURE_BITS, NODE_CODES
from ltm_r2.codec import digest, make_program
from ltm_r2.schemas import (
    MUMBRANE_SCHEMA,
    MumbraneCoordinate,
    MumbranePort,
    MumbraneProgram,
    MumbraneUnit,
    MumbraneVectorBundle,
)


def _code(text: str, offset: int) -> int:
    """Return a deterministic code that fits the packed uint16 contract."""
    if not 0 <= offset < 65535:
        raise ValueError("code offset outside packed range")
    return offset + int(hashlib.sha256(text.encode()).hexdigest()[:8], 16) % (65535 - offset)


def _walk(value: FormalExpression, prefix: tuple[int, ...] = ()):
    yield prefix, value
    for index, child in enumerate(value.args):
        yield from _walk(child, prefix + (index,))


def body_program(body_id: str, left: FormalExpression, right: FormalExpression, reality_key: str, source_text: str) -> MumbraneProgram:
    units: list[MumbraneUnit] = []
    ports: list[MumbranePort] = []
    coordinates: list[MumbraneCoordinate] = []
    bundles: list[MumbraneVectorBundle] = []
    vectors: list[tuple[float, ...]] = []
    class_code = CLASS_CODES["content"]
    mask = sum(FEATURE_BITS[name] for name in ("content", "context", "provenance", "identity", "integrity"))

    def add_expression(label: str, value: FormalExpression) -> int:
        start = len(units)
        nodes = tuple(_walk(value))
        indexes = {path: start + index for index, (path, _node) in enumerate(nodes)}
        for path, node in nodes:
            index = len(units)
            unit_id = f"{body_id}:{label}:{'.'.join(map(str, path)) or 'root'}"
            port_start = len(ports)
            for child_index, _child in enumerate(node.args):
                child_path = path + (child_index,)
                ports.append(MumbranePort(index, _code(f"child:{child_index}", 60000), child_index, indexes[child_path]))
            vector_index = len(vectors)
            vectors.append(tuple(float((int(hashlib.sha256(f"{unit_id}:{channel}".encode()).hexdigest()[:8], 16) % 200 - 100) / 200) for channel in range(8)))
            bundles.append(MumbraneVectorBundle(vector_index, None, None, vector_index, None))
            coordinates.append(MumbraneCoordinate(index, AXIS_CODES["scope"], _code(reality_key, 1)))
            units.append(MumbraneUnit(
                unit_id, MUMBRANE_SCHEMA, class_code, NODE_CODES["value"], mask,
                port_start, len(ports) - port_start, len(coordinates) - 1, 1,
                len(bundles) - 1, 1.0, 0,
                hashlib.sha256(f"{unit_id}|{node.op}|{node.value}".encode()).hexdigest(),
            ))
        return start

    left_start = add_expression("left", left)
    right_start = add_expression("right", right)
    root = len(units)
    ports.extend((
        MumbranePort(root, _code("left", 60000), 0, left_start),
        MumbranePort(root, _code("right", 60000), 1, right_start),
    ))
    coordinates.append(MumbraneCoordinate(root, AXIS_CODES["scope"], _code(reality_key, 1)))
    units.append(MumbraneUnit(
        f"{body_id}:body", MUMBRANE_SCHEMA, CLASS_CODES["constraint"], NODE_CODES["rule"], mask,
        len(ports) - 2, 2, len(coordinates) - 1, 1, None, 1.0, 0,
        hashlib.sha256(f"{body_id}|body|{reality_key}".encode()).hexdigest(),
    ))
    symbols = tuple(sorted({unit.unit_id for unit in units} | {body_id, reality_key}))
    return make_program(tuple(units), tuple(ports), tuple(coordinates), tuple(bundles), tuple(vectors), symbols, ((body_id, source_text),))


def formal_hash(left: FormalExpression, right: FormalExpression, reality_key: str) -> str:
    return digest({"left": left, "right": right, "reality_key": reality_key})
