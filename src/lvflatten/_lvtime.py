"""The value type carried by the ``Timestamp`` schema node."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import NamedTuple

from ._errors import DataError, SchemaError

LV_EPOCH = datetime(1904, 1, 1, tzinfo=timezone.utc)
_ONE = 1 << 64
_MICRO = 1_000_000


class LVTimestamp(NamedTuple):
    """A LabVIEW 128-bit time stamp: whole seconds and a 2**-64 fraction since 1904 UTC.

    ``seconds`` is a signed 64-bit count of seconds since 1904-01-01T00:00:00Z and
    ``fraction`` an unsigned 64-bit count of 2**-64 second units, exactly as LabVIEW
    stores them. Leap seconds are ignored, as in LabVIEW.

    >>> from datetime import datetime, timezone
    >>> from lvflatten import LVTimestamp
    >>> LVTimestamp.from_datetime(datetime(1970, 1, 1, tzinfo=timezone.utc))
    LVTimestamp(seconds=2082844800, fraction=0)
    >>> LVTimestamp(2082844800, 1 << 63).to_datetime().isoformat()
    '1970-01-01T00:00:00.500000+00:00'
    """

    seconds: int
    fraction: int

    @classmethod
    def from_datetime(cls, moment: datetime) -> LVTimestamp:
        """Convert a timezone-aware ``datetime``; a naive one raises :class:`SchemaError`.

        Microseconds map to the nearest-below 2**-64 fraction, so ``to_datetime`` gives the
        same instant back.

        >>> from datetime import datetime, timezone
        >>> LVTimestamp.from_datetime(datetime(1904, 1, 1, 0, 0, 1, tzinfo=timezone.utc))
        LVTimestamp(seconds=1, fraction=0)
        """
        if moment.tzinfo is None or moment.utcoffset() is None:
            raise SchemaError("from_datetime needs a timezone-aware datetime")
        delta = moment - LV_EPOCH
        seconds = delta.days * 86_400 + delta.seconds
        return cls(seconds, delta.microseconds * _ONE // _MICRO)

    def to_datetime(self) -> datetime:
        """Return the instant as a UTC ``datetime``, rounded to the nearest microsecond.

        A time stamp outside the years 1 to 9999 raises :class:`DataError`.

        >>> LVTimestamp(0, 0).to_datetime().isoformat()
        '1904-01-01T00:00:00+00:00'
        """
        micro = (self.fraction * _MICRO + _ONE // 2) >> 64
        try:
            return LV_EPOCH + timedelta(seconds=self.seconds, microseconds=micro)
        except OverflowError:
            raise DataError("time stamp is outside the range a datetime can hold") from None
