"""Pack and unpack LabVIEW booleans and boolean arrays.

LabVIEW flattens a boolean as a single byte (0 or 1), and a boolean array as an I32 count
followed by one byte per element. The byte-per-element layout is what LabVIEW's "Flatten To
String" emits and what the NI "Flattened Data" reference documents; it is not bit-packed.
"""

from __future__ import annotations

import struct

from ._errors import SchemaError
from ._reader import Reader


def pack_bool(value: object, out: bytearray) -> None:
    if not isinstance(value, bool):
        raise SchemaError(f"expected a bool, got {type(value).__name__}")
    out += b"\x01" if value else b"\x00"


def unpack_bool(reader: Reader) -> bool:
    return reader.take(1) != b"\x00"


def pack_bool_array(value: object, bo: str, out: bytearray) -> None:
    if not isinstance(value, (list, tuple)) or any(not isinstance(flag, bool) for flag in value):
        raise SchemaError("expected a list of bool for a boolean array")
    out += struct.pack(bo + "i", len(value))
    out += bytes(1 if flag else 0 for flag in value)


def unpack_bool_array(reader: Reader, bo: str) -> list[bool]:
    (count,) = struct.unpack(bo + "i", reader.take(4))
    if count < 0:
        raise SchemaError(f"boolean array length is negative: {count}")
    raw = reader.take(count)
    return [byte != 0 for byte in raw]
