"""Exceptions raised by the codec, and a helper that keeps their messages short.

Every error this package raises on purpose derives from :class:`LVFlattenError`. The two
families say whose fault it was: :class:`SchemaError` means the schema, the options or the
Python value are wrong; :class:`DataError` means the bytes do not fit the schema. Both also
derive from :class:`ValueError`, so generic ``except ValueError`` handlers keep working.
"""

from __future__ import annotations

_MAX_REPR = 40


class LVFlattenError(Exception):
    """Base class for every error this package raises.

    >>> from lvflatten import I32, LVFlattenError, unpack
    >>> try:
    ...     unpack(I32, b"\\x00")
    ... except LVFlattenError as exc:
    ...     print(type(exc).__name__)
    TruncatedDataError
    """


class SchemaError(LVFlattenError, ValueError):
    """The schema, an option, or the Python value does not match the declared type.

    >>> from lvflatten import I8, SchemaError, pack
    >>> try:
    ...     pack(I8, 300)
    ... except SchemaError as exc:
    ...     print(exc)
    value out of range for an 8-bit signed integer
    """


class DataError(LVFlattenError, ValueError):
    """The bytes do not fit the schema: a negative length, bad text, or leftover bytes.

    >>> from lvflatten import DataError, String, unpack
    >>> try:
    ...     unpack(String(), b"\\xff\\xff\\xff\\xff")
    ... except DataError as exc:
    ...     print(exc)
    string length is negative: -1
    """


class TruncatedDataError(DataError):
    """The byte buffer ended before the schema was fully read.

    >>> from lvflatten import DBL, TruncatedDataError, unpack
    >>> try:
    ...     unpack(DBL, b"\\x3f\\xf0")
    ... except TruncatedDataError as exc:
    ...     print(exc)
    need 8 bytes at offset 0, only 2 available
    """


class TrailingDataError(DataError):
    """The value was read completely but bytes were left over, usually a wrong schema.

    ``count`` holds the number of unread bytes.

    >>> from lvflatten import I16, TrailingDataError, unpack
    >>> try:
    ...     unpack(I16, b"\\x00\\x01\\x02")
    ... except TrailingDataError as exc:
    ...     print(exc.count, exc)
    1 1 trailing byte left after the value
    """

    def __init__(self, count: int) -> None:
        noun = "byte" if count == 1 else "bytes"
        super().__init__(f"{count} trailing {noun} left after the value")
        self.count = count


def short(value: object) -> str:
    """Return ``repr(value)`` cut to a bounded length, for use inside error messages."""
    text = repr(value)
    if len(text) <= _MAX_REPR:
        return text
    return text[: _MAX_REPR - 3] + "..."
