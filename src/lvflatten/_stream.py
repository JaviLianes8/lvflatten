"""Read one flattened value from the middle of a buffer, for back-to-back records."""

from __future__ import annotations

from typing import Literal

from ._buffer import as_view, release
from ._codec import _check_schema, _prefix, _unpack_node
from ._errors import SchemaError, short
from ._reader import Reader
from ._schema import Schema


def unpack_from(
    schema: Schema,
    data: bytes | bytearray | memoryview,
    offset: int = 0,
    *,
    byte_order: Literal["big", "little"] = "big",
) -> tuple[object, int]:
    """Read one value starting at ``offset`` and return ``(value, next_offset)``.

    Unlike :func:`unpack`, bytes after the value are allowed: ``next_offset`` points at
    them, like the "rest of the flattened string" output of LabVIEW's Unflatten From String.
    Use it to walk several flattened values sent back to back. Sizes are always read from
    the data (there is no ``prepend_size``). A bad ``offset`` raises :class:`SchemaError`.

    >>> from lvflatten import I16, String, unpack_from
    >>> stream = bytes.fromhex("0007" "00000002" "6f6b" "0009")
    >>> unpack_from(I16, stream)
    (7, 2)
    >>> unpack_from(String(), stream, 2)
    ('ok', 8)
    """
    node = _check_schema(schema)
    bo = _prefix(byte_order)
    raw = as_view(data)  # no per-call copy, so walking a long buffer stays linear
    try:
        if isinstance(offset, bool) or not isinstance(offset, int) or not 0 <= offset <= len(raw):
            raise SchemaError(f"offset must be an int from 0 to {len(raw)}, got {short(offset)}")
        reader = Reader(raw, offset, stream=True)
        try:
            value = _unpack_node(node, reader, bo)
        except RecursionError:
            raise SchemaError("the schema nests too deeply") from None
        return value, reader.position
    finally:
        release(raw)  # an error kept alive by the caller must not pin their bytearray
