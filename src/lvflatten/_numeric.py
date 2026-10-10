"""Pack and unpack LabVIEW integer and IEEE 754 float scalars."""

from __future__ import annotations

import struct

from ._errors import SchemaError
from ._reader import Reader
from ._schema import FloatType, IntType

_INT_CHARS = {8: "b", 16: "h", 32: "i", 64: "q"}


def _int_format(schema: IntType) -> str:
    try:
        char = _INT_CHARS[schema.bits]
    except KeyError:  # pragma: no cover - the schema builders never create other widths
        raise SchemaError(f"unsupported integer width: {schema.bits}") from None
    return char if schema.signed else char.upper()


def pack_int(schema: IntType, value: object, bo: str, out: bytearray) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SchemaError(f"expected an int for a {schema.bits}-bit integer")
    try:
        out += struct.pack(bo + _int_format(schema), value)
    except struct.error as exc:
        raise SchemaError(f"value out of range for a {schema.bits}-bit integer") from exc


def unpack_int(schema: IntType, reader: Reader, bo: str) -> int:
    (value,) = struct.unpack(bo + _int_format(schema), reader.take(schema.bits // 8))
    return int(value)


def pack_float(schema: FloatType, value: object, bo: str, out: bytearray) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SchemaError("expected a real number for a float")
    out += struct.pack(bo + ("d" if schema.double else "f"), float(value))


def unpack_float(schema: FloatType, reader: Reader, bo: str) -> float:
    size = 8 if schema.double else 4
    (value,) = struct.unpack(bo + ("d" if schema.double else "f"), reader.take(size))
    return float(value)
