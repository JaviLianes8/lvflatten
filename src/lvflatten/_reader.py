"""A forward-only cursor over a byte buffer, with a budget against output blow-up."""

from __future__ import annotations

from ._errors import DataError, TruncatedDataError

FREE_FLOOR = 1024


class Reader:
    """Hands out fixed-size slices of a buffer and raises when it runs short.

    Some values cost no input bytes (the rows of an array with a zero dimension, or the
    containers inside an array of empty clusters). ``spend_free`` charges those against a
    budget of ``FREE_FLOOR`` objects plus one per input byte, so a few hostile bytes cannot ask
    for billions of objects while small legitimate shapes still decode. The input bytes are
    the whole buffer for a value that must fill it, and only the bytes read so far when the
    value is one of several back to back (``stream``), so a long buffer cannot lend its
    size to every value read from it.
    """

    __slots__ = ("_data", "_pos", "_spent", "_start", "_stream")

    def __init__(self, data: bytes | memoryview, start: int = 0, *, stream: bool = False) -> None:
        self._data = data
        self._pos = start
        self._start = start
        self._spent = 0
        self._stream = stream

    def take(self, count: int) -> bytes:
        """Return the next ``count`` bytes, or raise if the buffer is too short."""
        end = self._pos + count
        if end > len(self._data):
            raise TruncatedDataError(
                f"need {count} bytes at offset {self._pos}, "
                f"only {len(self._data) - self._pos} available"
            )
        chunk = bytes(self._data[self._pos : end])  # no copy for bytes, one slice for a view
        self._pos = end
        return chunk

    def spend_free(self, count: int) -> None:
        """Charge ``count`` objects that consume no input; raise once the budget runs out."""
        self._spent += count
        end = self._pos if self._stream else len(self._data)
        if self._spent > FREE_FLOOR + end - self._start:
            raise DataError(
                f"the data declares {count} empty items, more than its size can justify"
            )

    @property
    def position(self) -> int:
        """Offset of the next unread byte."""
        return self._pos

    @property
    def remaining(self) -> int:
        """How many bytes are still unread."""
        return len(self._data) - self._pos

    def done(self) -> bool:
        """True once every byte has been consumed."""
        return self._pos >= len(self._data)
