"""Pack and unpack LabVIEW booleans and bit-packed boolean arrays."""

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
    packed = bytearray((len(value) + 7) // 8)
    for index, flag in enumerate(value):
        if flag:
            packed[index // 8] |= 0x80 >> (index % 8)
    out += packed


def unpack_bool_array(reader: Reader, bo: str) -> list[bool]:
    (count,) = struct.unpack(bo + "i", reader.take(4))
    if count < 0:
        raise SchemaError(f"boolean array length is negative: {count}")
    raw = reader.take((count + 7) // 8)
    return [bool(raw[index // 8] & (0x80 >> (index % 8))) for index in range(count)]
