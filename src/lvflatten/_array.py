"""Pack and unpack LabVIEW arrays (one I32 size per dimension, row-major elements)."""

from __future__ import annotations

import struct
from collections.abc import Callable

from ._errors import SchemaError
from ._reader import Reader
from ._schema import Array, Schema

PackNode = Callable[[Schema, object, str, bytearray], None]
UnpackNode = Callable[[Schema, Reader, str], object]


def _shape(value: object, ndims: int) -> list[int]:
    dims: list[int] = []
    level: object = value
    for _ in range(ndims):
        if not isinstance(level, (list, tuple)):
            raise SchemaError("array value has fewer dimensions than the schema")
        dims.append(len(level))
        level = level[0] if level else []
    return dims


def _flatten(value: object, ndims: int) -> list[object]:
    if not isinstance(value, (list, tuple)):
        raise SchemaError("expected a (possibly nested) list for an array")
    if ndims == 1:
        return list(value)
    flat: list[object] = []
    for row in value:
        flat.extend(_flatten(row, ndims - 1))
    return flat


def _nest(flat: list[object], dims: list[int]) -> list[object]:
    if len(dims) == 1:
        return flat
    inner = dims[1:]
    block = 1
    for size in inner:
        block *= size
    return [_nest(flat[i * block : (i + 1) * block], inner) for i in range(dims[0])]


def pack_array(schema: Array, value: object, bo: str, out: bytearray, pack_node: PackNode) -> None:
    dims = _shape(value, schema.ndims)
    for size in dims:
        out += struct.pack(bo + "i", size)
    for element in _flatten(value, schema.ndims):
        pack_node(schema.element, element, bo, out)


def unpack_array(schema: Array, reader: Reader, bo: str, unpack_node: UnpackNode) -> list[object]:
    dims: list[int] = []
    for _ in range(schema.ndims):
        (size,) = struct.unpack(bo + "i", reader.take(4))
        if size < 0:
            raise SchemaError(f"array dimension is negative: {size}")
        dims.append(size)
    total = 1
    for size in dims:
        total *= size
    flat = [unpack_node(schema.element, reader, bo) for _ in range(total)]
    return _nest(flat, dims)
