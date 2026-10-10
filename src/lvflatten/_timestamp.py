"""Pack and unpack the LabVIEW 128-bit timestamp (seconds and fraction since 1904)."""

from __future__ import annotations

import struct

from ._errors import SchemaError
from ._reader import Reader
from ._schema import LVTimestamp

_U64_LIMIT = 1 << 64


def pack_timestamp(value: object, bo: str, out: bytearray) -> None:
    if not isinstance(value, tuple) or len(value) != 2:
        raise SchemaError("expected an LVTimestamp, i.e. a (seconds, fraction) pair")
    seconds, fraction = value
    if isinstance(seconds, bool) or isinstance(fraction, bool):
        raise SchemaError("timestamp seconds and fraction must be integers, not bool")
    if not isinstance(seconds, int) or not isinstance(fraction, int):
        raise SchemaError("timestamp seconds and fraction must be integers")
    if not 0 <= fraction < _U64_LIMIT:
        raise SchemaError("timestamp fraction must fit in an unsigned 64-bit integer")
    out += struct.pack(bo + "qQ", seconds, fraction)


def unpack_timestamp(reader: Reader, bo: str) -> LVTimestamp:
    seconds, fraction = struct.unpack(bo + "qQ", reader.take(16))
    return LVTimestamp(int(seconds), int(fraction))
