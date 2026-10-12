"""Pack and unpack the LabVIEW 128-bit timestamp (I64 seconds, U64 fraction, since 1904)."""

from __future__ import annotations

import struct

from ._errors import SchemaError
from ._lvtime import LVTimestamp
from ._reader import Reader

_U64_LIMIT = 1 << 64
_I64_LIMIT = 1 << 63


def pack_timestamp(value: object, bo: str, out: bytearray) -> None:
    if not isinstance(value, tuple) or len(value) != 2:
        raise SchemaError("expected an LVTimestamp, i.e. a (seconds, fraction) pair")
    seconds, fraction = value
    for part in (seconds, fraction):
        if isinstance(part, bool) or not isinstance(part, int):
            raise SchemaError("timestamp seconds and fraction must be integers")
    if not -_I64_LIMIT <= seconds < _I64_LIMIT:
        raise SchemaError("timestamp seconds must fit in a signed 64-bit integer")
    if not 0 <= fraction < _U64_LIMIT:
        raise SchemaError("timestamp fraction must fit in an unsigned 64-bit integer")
    out += struct.pack(bo + "qQ", seconds, fraction)


def unpack_timestamp(reader: Reader, bo: str) -> LVTimestamp:
    seconds, fraction = struct.unpack(bo + "qQ", reader.take(16))
    return LVTimestamp(int(seconds), int(fraction))
