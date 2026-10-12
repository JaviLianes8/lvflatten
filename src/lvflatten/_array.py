"""Pack and unpack LabVIEW arrays (one I32 size per dimension, row-major elements)."""

from __future__ import annotations

import struct
from collections.abc import Callable

from ._compound import Array
from ._errors import DataError, SchemaError, TruncatedDataError, count_text
from ._reader import Reader
from ._schema import Schema
from ._sizes import containers, fixed_size

PackNode = Callable[[Schema, object, str, bytearray], None]
UnpackNode = Callable[[Schema, Reader, str], object]

_I32_MAX = 0x7FFFFFFF


def _items(value: object) -> list[object]:
    """Copy one level of the value into a plain list, so lengths cannot lie."""
    if not isinstance(value, (list, tuple)):
        raise SchemaError("expected a list nested as deep as the array's dimensions")
    return list(iter(value))  # iter() ignores an overridden __len__


def _shape(value: object, ndims: int) -> list[int]:
    dims: list[int] = []
    level: object = value
    for _ in range(ndims):
        items = _items(level)
        if len(items) > _I32_MAX:
            raise SchemaError("an array dimension longer than 2**31 - 1 cannot be flattened")
        dims.append(len(items))
        level = items[0] if items else []
    return dims


def _flatten(value: object, dims: list[int], flat: list[object]) -> None:
    items = _items(value)
    if len(items) != dims[0]:
        raise SchemaError("array rows must all have the same length (the array is ragged)")
    if len(dims) == 1:
        flat.extend(items)
        return
    for row in items:
        _flatten(row, dims[1:], flat)


def _nest(flat: list[object], dims: list[int]) -> list[object]:
    if len(dims) == 1:
        return flat
    inner = dims[1:]
    block = 1
    for size in inner:
        block *= size
    return [_nest(flat[i * block : (i + 1) * block], inner) for i in range(dims[0])]


def _empty_rows(dims: list[int]) -> int:
    """How many list objects nesting creates when the array holds no elements at all."""
    rows, product = 0, 1
    for size in dims[:-1]:
        product *= size
        rows += product
        if not product:
            break
    return rows


def pack_array(schema: Array, value: object, bo: str, out: bytearray, pack_node: PackNode) -> None:
    dims = _shape(value, schema.ndims)
    flat: list[object] = []
    _flatten(value, dims, flat)
    for size in dims:
        out += struct.pack(bo + "i", size)
    for element in flat:
        pack_node(schema.element, element, bo, out)


def unpack_array(schema: Array, reader: Reader, bo: str, unpack_node: UnpackNode) -> list[object]:
    dims: list[int] = []
    for _ in range(schema.ndims):
        (size,) = struct.unpack(bo + "i", reader.take(4))
        if size < 0:
            raise DataError(f"array dimension is negative: {size}")
        dims.append(size)
    total = 1
    for size in dims:
        total *= size
    element_size = fixed_size(schema.element)
    if total == 0:
        reader.spend_free(_empty_rows(dims))
    elif element_size == 0:
        reader.spend_free(total * containers(schema.element) + _empty_rows(dims))
    elif element_size is not None and total * element_size > reader.remaining:
        raise TruncatedDataError(
            f"array declares {count_text(total)} elements of {element_size} bytes, "
            f"only {reader.remaining} bytes available"
        )
    flat = [unpack_node(schema.element, reader, bo) for _ in range(total)]
    return _nest(flat, dims)
