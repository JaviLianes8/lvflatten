"""Exceptions raised by the codec."""

from __future__ import annotations


class LVFlattenError(Exception):
    """Base class for every error this package raises."""


class SchemaError(LVFlattenError):
    """The schema disagrees with the value, the options, or the declared type."""


class TruncatedDataError(LVFlattenError):
    """The byte buffer ended before the schema was fully read."""
