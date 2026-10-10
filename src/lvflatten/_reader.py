"""A forward-only cursor over a byte buffer."""

from __future__ import annotations

from ._errors import TruncatedDataError


class Reader:
    """Hands out fixed-size slices of a buffer and raises when it runs short."""

    __slots__ = ("_data", "_pos")

    def __init__(self, data: bytes) -> None:
        self._data = data
        self._pos = 0

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

    @property
    def remaining(self) -> int:
        """How many bytes are still unread."""
        return len(self._data) - self._pos

    def done(self) -> bool:
        """True once every byte has been consumed."""
        return self._pos >= len(self._data)
