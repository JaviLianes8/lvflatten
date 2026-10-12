"""The public codec: dispatch pack and unpack over a schema, with the top-level size toggle."""

from __future__ import annotations

from typing import Literal

from ._array import pack_array, unpack_array
from ._cluster import pack_cluster, unpack_cluster
from ._compound import Array, Cluster, String
from ._errors import DataError, SchemaError, TrailingDataError, short
from ._ext import pack_ext, unpack_ext
from ._numeric import pack_bool, pack_float, pack_int, unpack_bool, unpack_float, unpack_int
from ._reader import Reader
from ._schema import BoolType, BytesType, ExtType, FloatType, IntType, Schema, TimestampType
from ._sizes import fixed_size
from ._string import decode_text, pack_bytes, pack_string, unpack_bytes, unpack_string
from ._timestamp import pack_timestamp, unpack_timestamp

_BYTE_ORDER = {"big": ">", "little": "<"}


def _prefix(byte_order: object) -> str:
    if isinstance(byte_order, str) and byte_order in _BYTE_ORDER:
        return _BYTE_ORDER[byte_order]
    raise SchemaError(f"byte_order must be 'big' or 'little', got {short(byte_order)}")


def _check_flag(prepend_size: object) -> bool:
    if not isinstance(prepend_size, bool):
        raise SchemaError(f"prepend_size must be True or False, got {short(prepend_size)}")
    return prepend_size


def _as_view(data: object) -> bytes | memoryview:
    """Return ``data`` as bytes, or as a flat byte view of it, without copying the buffer."""
    if isinstance(data, bytes):
        return data
    if not isinstance(data, (bytearray, memoryview)):
        raise TypeError(f"data must be bytes-like, got {type(data).__name__}")
    try:
        view = memoryview(data)
        return view.cast("B") if view.c_contiguous else memoryview(view.tobytes())
    except ValueError:
        raise TypeError("data is a released or unusable memoryview") from None


def _as_data(data: object) -> bytes:
    return bytes(_as_view(data))


def _check_schema(schema: object) -> Schema:
    if not isinstance(schema, Schema):
        raise SchemaError(f"expected a schema node, got {short(schema)}")
    return schema


def _pack_node(schema: Schema, value: object, bo: str, out: bytearray) -> None:
    if isinstance(schema, IntType):
        pack_int(schema, value, bo, out)
    elif isinstance(schema, FloatType):
        pack_float(schema, value, bo, out)
    elif isinstance(schema, ExtType):
        pack_ext(value, bo, out)
    elif isinstance(schema, BoolType):
        pack_bool(value, out)
    elif isinstance(schema, TimestampType):
        pack_timestamp(value, bo, out)
    elif isinstance(schema, String):
        pack_string(schema, value, bo, out)
    elif isinstance(schema, BytesType):
        pack_bytes(value, bo, out)
    elif isinstance(schema, Array):
        pack_array(schema, value, bo, out, _pack_node)
    elif isinstance(schema, Cluster):
        pack_cluster(schema, value, bo, out, _pack_node)
    else:
        raise SchemaError(f"unsupported schema: {short(schema)}")


def _unpack_node(schema: Schema, reader: Reader, bo: str) -> object:
    if isinstance(schema, IntType):
        return unpack_int(schema, reader, bo)
    if isinstance(schema, FloatType):
        return unpack_float(schema, reader, bo)
    if isinstance(schema, ExtType):
        return unpack_ext(reader, bo)
    if isinstance(schema, BoolType):
        return unpack_bool(reader)
    if isinstance(schema, TimestampType):
        return unpack_timestamp(reader, bo)
    if isinstance(schema, String):
        return unpack_string(schema, reader, bo)
    if isinstance(schema, BytesType):
        return unpack_bytes(reader, bo)
    if isinstance(schema, Array):
        return unpack_array(schema, reader, bo, _unpack_node)
    if isinstance(schema, Cluster):
        return unpack_cluster(schema, reader, bo, _unpack_node)
    raise SchemaError(f"unsupported schema: {short(schema)}")


def _unpack_without_size(schema: String | BytesType | Array, data: bytes, bo: str) -> object:
    if isinstance(schema, String):
        return decode_text(schema, data)
    if isinstance(schema, BytesType):
        return data
    if schema.ndims != 1:
        raise SchemaError("prepend_size=False needs a one-dimensional array to unpack")
    size = fixed_size(schema.element)
    if not size:
        raise SchemaError("prepend_size=False needs fixed-size, non-empty array elements")
    if len(data) % size:
        raise DataError(f"{len(data)} bytes is not a whole number of {size}-byte elements")
    reader = Reader(data)
    return [_unpack_node(schema.element, reader, bo) for _ in range(len(data) // size)]


def pack(
    schema: Schema,
    value: object,
    *,
    byte_order: Literal["big", "little"] = "big",
    prepend_size: bool = True,
) -> bytes:
    """Flatten ``value`` to bytes as the LabVIEW type described by ``schema``.

    ``byte_order`` is "big" (the LabVIEW default) or "little". When ``prepend_size`` is false
    the leading I32 length of a top-level string or ``Bytes``, or the leading dimension sizes
    of a top-level array, are left out, mirroring LabVIEW's "prepend array or string size?"
    terminal. Nested strings and arrays always keep their own size.

    Raises :class:`SchemaError` when the value does not match the schema.

    >>> from lvflatten import I32, String, pack
    >>> pack(I32, -19).hex()
    'ffffffed'
    >>> pack(String(), "ABC", prepend_size=False)
    b'ABC'
    """
    node = _check_schema(schema)
    bo = _prefix(byte_order)
    _check_flag(prepend_size)
    out = bytearray()
    try:
        _pack_node(node, value, bo, out)
    except RecursionError:
        raise SchemaError("the schema or value nests too deeply") from None
    if not prepend_size:
        if isinstance(node, (String, BytesType)):
            del out[:4]
        elif isinstance(node, Array):
            del out[: 4 * node.ndims]
    return bytes(out)


def unpack(
    schema: Schema,
    data: bytes | bytearray | memoryview,
    *,
    byte_order: Literal["big", "little"] = "big",
    prepend_size: bool = True,
) -> object:
    """Rebuild the value from flattened ``data`` using ``schema``.

    The whole buffer must be consumed: leftover bytes raise :class:`TrailingDataError`, which
    catches a wrong schema or size. Short data raises :class:`TruncatedDataError` and other
    malformed data :class:`DataError`. With ``prepend_size`` false a top-level string takes
    the whole buffer and a top-level one-dimensional array of fixed-size elements is read to
    the end. ``data`` may be any bytes-like object; anything else raises ``TypeError``.

    >>> from lvflatten import I32, Array, unpack
    >>> unpack(Array(I32), bytes.fromhex("000000020000000100000002"))
    [1, 2]
    """
    node = _check_schema(schema)
    bo = _prefix(byte_order)
    _check_flag(prepend_size)
    raw = _as_data(data)
    try:
        if not prepend_size and isinstance(node, (String, BytesType, Array)):
            return _unpack_without_size(node, raw, bo)
        reader = Reader(raw)
        value = _unpack_node(node, reader, bo)
    except RecursionError:
        raise SchemaError("the schema nests too deeply") from None
    if not reader.done():
        raise TrailingDataError(reader.remaining)
    return value
