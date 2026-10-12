"""Pack and unpack LabVIEW integer, IEEE 754 float and boolean scalars."""

from __future__ import annotations

import struct

from ._errors import SchemaError
from ._reader import Reader
from ._schema import FloatType, IntType

_INT_CHARS = {8: "b", 16: "h", 32: "i", 64: "q"}


def _int_format(schema: IntType) -> str:
    char = _INT_CHARS[schema.bits]
    return char if schema.signed else char.upper()


def _kind(schema: IntType) -> str:
    return f"{schema.bits}-bit {'signed' if schema.signed else 'unsigned'} integer"


def _article(schema: IntType) -> str:
    return "an" if schema.bits == 8 else "a"


def pack_int(schema: IntType, value: object, bo: str, out: bytearray) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SchemaError(f"expected an int for a {_kind(schema)}, got {type(value).__name__}")
    try:
        out += struct.pack(bo + _int_format(schema), value)
    except (struct.error, OverflowError):
        raise SchemaError(f"value out of range for {_article(schema)} {_kind(schema)}") from None


def unpack_int(schema: IntType, reader: Reader, bo: str) -> int:
    (value,) = struct.unpack(bo + _int_format(schema), reader.take(schema.bits // 8))
    return int(value)


def pack_float(schema: FloatType, value: object, bo: str, out: bytearray) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SchemaError(f"expected a real number for a float, got {type(value).__name__}")
    try:
        out += struct.pack(bo + ("d" if schema.double else "f"), float(value))
    except (struct.error, OverflowError):
        raise SchemaError("value out of range for a " + repr(schema)) from None


def unpack_float(schema: FloatType, reader: Reader, bo: str) -> float:
    size = 8 if schema.double else 4
    (value,) = struct.unpack(bo + ("d" if schema.double else "f"), reader.take(size))
    return float(value)


def pack_bool(value: object, out: bytearray) -> None:
    if not isinstance(value, bool):
        raise SchemaError(f"expected a bool, got {type(value).__name__}")
    out += b"\x01" if value else b"\x00"


def unpack_bool(reader: Reader) -> bool:
    return reader.take(1) != b"\x00"
