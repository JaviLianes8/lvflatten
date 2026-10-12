"""A forward-only cursor over a byte buffer, with a budget against output blow-up."""

from __future__ import annotations

from ._errors import DataError, TruncatedDataError


class Reader:
    """Hands out fixed-size slices of a buffer and raises when it runs short.

    Some values cost no input bytes (the rows of an array with a zero dimension, or the
    elements of an array of empty clusters). ``spend_free`` charges those against a budget of
    one object per input byte, so a few hostile bytes cannot ask for billions of objects.
    """

    __slots__ = ("_data", "_free", "_pos")

    def __init__(self, data: bytes, start: int = 0) -> None:
        self._data = data
        self._pos = start
        self._free = len(data) - start

    def take(self, count: int) -> bytes:
        """Return the next ``count`` bytes, or raise if the buffer is too short."""
        end = self._pos + count
        if end > len(self._data):
            raise TruncatedDataError(
                f"need {count} bytes at offset {self._pos}, "
                f"only {len(self._data) - self._pos} available"
            )
        chunk = self._data[self._pos : end]
        self._pos = end
        return chunk

    def spend_free(self, count: int) -> None:
        """Charge ``count`` objects that consume no input; raise once the budget runs out."""
        self._free -= count
        if self._free < 0:
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
