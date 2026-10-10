"""The public codec: dispatch pack and unpack over a schema, with the top-level size toggle."""

from __future__ import annotations

from ._array import pack_array, unpack_array
from ._bool import pack_bool, pack_bool_array, unpack_bool, unpack_bool_array
from ._cluster import pack_cluster, unpack_cluster
from ._errors import LVFlattenError, SchemaError
from ._ext import pack_ext, unpack_ext
from ._numeric import pack_float, pack_int, unpack_float, unpack_int
from ._reader import Reader
from ._schema import (
    Array,
    BoolArrayType,
    BoolType,
    Cluster,
    ExtType,
    FloatType,
    IntType,
    Schema,
    String,
    TimestampType,
)
from ._string import pack_string, unpack_string
from ._timestamp import pack_timestamp, unpack_timestamp

_BYTE_ORDER = {"big": ">", "little": "<"}


def _prefix(byte_order: str) -> str:
    try:
        return _BYTE_ORDER[byte_order]
    except KeyError:
        raise SchemaError(f"byte_order must be 'big' or 'little', got {byte_order!r}") from None


def _pack_node(schema: Schema, value: object, bo: str, out: bytearray) -> None:
    if isinstance(schema, IntType):
        pack_int(schema, value, bo, out)
    elif isinstance(schema, FloatType):
        pack_float(schema, value, bo, out)
    elif isinstance(schema, ExtType):
        pack_ext(value, bo, out)
    elif isinstance(schema, BoolType):
        pack_bool(value, out)
    elif isinstance(schema, BoolArrayType):
        pack_bool_array(value, bo, out)
    elif isinstance(schema, TimestampType):
        pack_timestamp(value, bo, out)
    elif isinstance(schema, String):
        pack_string(schema, value, bo, out)
    elif isinstance(schema, Array):
        pack_array(schema, value, bo, out, _pack_node)
    elif isinstance(schema, Cluster):
        pack_cluster(schema, value, bo, out, _pack_node)
    else:  # pragma: no cover - the Schema union is exhaustive above
        raise SchemaError(f"unsupported schema: {schema!r}")


def _unpack_node(schema: Schema, reader: Reader, bo: str) -> object:
    if isinstance(schema, IntType):
        return unpack_int(schema, reader, bo)
    if isinstance(schema, FloatType):
        return unpack_float(schema, reader, bo)
    if isinstance(schema, ExtType):
        return unpack_ext(reader, bo)
    if isinstance(schema, BoolType):
        return unpack_bool(reader)
    if isinstance(schema, BoolArrayType):
        return unpack_bool_array(reader, bo)
    if isinstance(schema, TimestampType):
        return unpack_timestamp(reader, bo)
    if isinstance(schema, String):
        return unpack_string(schema, reader, bo)
    if isinstance(schema, Array):
        return unpack_array(schema, reader, bo, _unpack_node)
    if isinstance(schema, Cluster):
        return unpack_cluster(schema, reader, bo, _unpack_node)
    raise SchemaError(f"unsupported schema: {schema!r}")  # pragma: no cover - exhaustive above


def _fixed_size(schema: Schema) -> int | None:
    """Byte size of a fixed-size schema, or None if it carries a length of its own."""
    if isinstance(schema, IntType):
        return schema.bits // 8
    if isinstance(schema, FloatType):
        return 8 if schema.double else 4
    if isinstance(schema, ExtType):
        return 16
    if isinstance(schema, BoolType):
        return 1
    if isinstance(schema, TimestampType):
        return 16
    if isinstance(schema, Cluster):
        total = 0
        for _, field_schema in schema.fields:
            size = _fixed_size(field_schema)
            if size is None:
                return None
            total += size
        return total
    return None


def _strip_top_size(schema: Schema, out: bytearray) -> bytearray:
    if isinstance(schema, String):
        return out[4:]
    if isinstance(schema, Array):
        return out[4 * schema.ndims :]
    return out


def _unpack_without_size(schema: Schema, data: bytes, bo: str) -> object:
    if isinstance(schema, String):
        return data.decode(schema.encoding)
    if isinstance(schema, Array):
        if schema.ndims != 1:
            raise SchemaError("prepend_size=False needs a one-dimensional array")
        size = _fixed_size(schema.element)
        if size is None or size == 0:
            raise SchemaError("prepend_size=False needs fixed-size array elements")
        if len(data) % size:
            raise SchemaError("data length is not a whole number of elements")
        reader = Reader(data)
        return [_unpack_node(schema.element, reader, bo) for _ in range(len(data) // size)]
    raise SchemaError("prepend_size=False only applies to a top-level string or array")


def pack(
    schema: Schema,
    value: object,
    *,
    byte_order: str = "big",
    prepend_size: bool = True,
) -> bytes:
    """Flatten ``value`` to bytes as the LabVIEW type described by ``schema``.

    ``byte_order`` is "big" (the LabVIEW default) or "little". When ``prepend_size`` is false
    the leading I32 length of a top-level string, or the leading dimension sizes of a top-level
    array, are omitted, mirroring LabVIEW's "prepend array or string size?" terminal.
    """
    bo = _prefix(byte_order)
    out = bytearray()
    _pack_node(schema, value, bo, out)
    if not prepend_size:
        out = _strip_top_size(schema, out)
    return bytes(out)


def unpack(
    schema: Schema,
    data: bytes,
    *,
    byte_order: str = "big",
    prepend_size: bool = True,
) -> object:
    """Rebuild the value from flattened ``data`` using ``schema``.

    The whole buffer must be consumed: trailing bytes raise, which catches a wrong schema or
    size. With ``prepend_size`` false a top-level string takes the whole buffer and a top-level
    one-dimensional array of fixed-size elements is read to the end.
    """
    bo = _prefix(byte_order)
    if not prepend_size and isinstance(schema, (String, Array)):
        return _unpack_without_size(schema, data, bo)
    reader = Reader(data)
    value = _unpack_node(schema, reader, bo)
    if not reader.done():
        raise LVFlattenError(f"{reader.remaining} trailing bytes left after the value")
    return value
