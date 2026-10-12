"""Turn any bytes-like input into a flat byte sequence without copying it when possible."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing_extensions import Buffer
elif sys.version_info >= (3, 12):
    from collections.abc import Buffer
else:  # what runtime hint resolution sees before Python 3.12
    Buffer = bytes | bytearray | memoryview

__all__ = ["Buffer", "as_view", "release"]


def as_view(data: object) -> bytes | memoryview:
    """Return ``data`` as bytes or as a one-dimensional byte view of it.

    Anything that supports the buffer protocol is accepted (``bytes``, ``bytearray``,
    ``memoryview``, ``array.array``, ``mmap``, ...). Contiguous buffers and strided views of
    single bytes are read in place; any other layout is copied once.
    """
    if isinstance(data, bytes):
        return data
    if isinstance(data, str):
        raise TypeError("data must be bytes-like, got str")
    try:
        view = memoryview(data)  # type: ignore[arg-type]
    except TypeError:
        raise TypeError(f"data must be bytes-like, got {type(data).__name__}") from None
    except ValueError:
        raise TypeError("data is a released or unusable memoryview") from None
    try:
        if view.c_contiguous:
            return view.cast("B")
        if view.ndim == 1 and view.itemsize == 1 and view.format in ("B", "b", "c"):
            return view
        return memoryview(view.tobytes())
    except ValueError:
        raise TypeError("data is a released or unusable memoryview") from None


def release(raw: bytes | memoryview) -> None:
    """Drop the export a view holds, so the caller may resize its buffer again."""
    if isinstance(raw, memoryview):
        raw.release()
