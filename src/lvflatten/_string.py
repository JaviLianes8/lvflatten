"""Pack and unpack LabVIEW strings (an I32 byte count then the encoded bytes)."""

from __future__ import annotations

import struct

from ._errors import SchemaError
from ._reader import Reader
from ._schema import String


def pack_string(schema: String, value: object, bo: str, out: bytearray) -> None:
    if not isinstance(value, str):
        raise SchemaError(f"expected a str, got {type(value).__name__}")
    encoded = value.encode(schema.encoding)
    out += struct.pack(bo + "i", len(encoded))
    out += encoded


def unpack_string(schema: String, reader: Reader, bo: str) -> str:
    (length,) = struct.unpack(bo + "i", reader.take(4))
    if length < 0:
        raise SchemaError(f"string length is negative: {length}")
    return reader.take(length).decode(schema.encoding)
