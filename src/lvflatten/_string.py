"""Pack and unpack LabVIEW strings, as text or as raw bytes (an I32 count then the bytes)."""

from __future__ import annotations

import struct

from ._compound import String
from ._errors import DataError, SchemaError
from ._reader import Reader


def encode_text(schema: String, value: object) -> bytes:
    if not isinstance(value, str):
        raise SchemaError(f"expected a str, got {type(value).__name__}")
    try:
        return value.encode(schema.encoding)
    except UnicodeError:
        raise SchemaError(f"text cannot be encoded as {schema.encoding}") from None


def decode_text(schema: String, raw: bytes) -> str:
    try:
        return raw.decode(schema.encoding)
    except UnicodeError as exc:
        start = getattr(exc, "start", "?")
        raise DataError(f"bytes are not valid {schema.encoding} text (offset {start})") from None


def as_bytes(value: object) -> bytes:
    if not isinstance(value, (bytes, bytearray, memoryview)):
        raise SchemaError(f"expected bytes, got {type(value).__name__}")
    return bytes(value)


def _write(raw: bytes, bo: str, out: bytearray) -> None:
    if len(raw) > 0x7FFFFFFF:
        raise SchemaError("a string longer than 2**31 - 1 bytes cannot be flattened")
    out += struct.pack(bo + "i", len(raw))
    out += raw


def _read(reader: Reader, bo: str) -> bytes:
    (length,) = struct.unpack(bo + "i", reader.take(4))
    if length < 0:
        raise DataError(f"string length is negative: {length}")
    return reader.take(length)


def pack_string(schema: String, value: object, bo: str, out: bytearray) -> None:
    _write(encode_text(schema, value), bo, out)


def unpack_string(schema: String, reader: Reader, bo: str) -> str:
    return decode_text(schema, _read(reader, bo))


def pack_bytes(value: object, bo: str, out: bytearray) -> None:
    _write(as_bytes(value), bo, out)


def unpack_bytes(reader: Reader, bo: str) -> bytes:
    return bytes(_read(reader, bo))
