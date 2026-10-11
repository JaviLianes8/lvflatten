"""The typed schema: the caller declares the LabVIEW type and these nodes describe it.

Flattened data carries no type information, so every pack or unpack needs one of these
nodes to say how the bytes should be read. Scalars are ready-made singletons (``I32``,
``DBL``, ``EXT``, ``Boolean``, ``Timestamp``, ...); ``String``, ``Array`` and ``Cluster``
are built for the shape at hand.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import NamedTuple

from ._errors import SchemaError


class LVTimestamp(NamedTuple):
    """A LabVIEW 128-bit timestamp: whole seconds since 1904 and a 2**-64 fraction."""

    seconds: int
    fraction: int


@dataclass(frozen=True)
class IntType:
    """A fixed-width LabVIEW integer, signed or unsigned."""

    bits: int
    signed: bool


@dataclass(frozen=True)
class FloatType:
    """A LabVIEW IEEE 754 float: single (SGL) when ``double`` is false, else double (DBL)."""

    double: bool


@dataclass(frozen=True)
class ExtType:
    """A LabVIEW extended-precision float (80-bit, stored big-endian in 16 bytes)."""


@dataclass(frozen=True)
class BoolType:
    """A LabVIEW boolean, flattened as a single byte (0 or 1)."""


@dataclass(frozen=True)
class BoolArrayType:
    """A LabVIEW boolean array: an I32 count then one byte per element (0 or 1)."""


@dataclass(frozen=True)
class TimestampType:
    """A LabVIEW 128-bit timestamp value."""


@dataclass(frozen=True)
class String:
    """A LabVIEW string: an I32 byte count followed by the encoded bytes."""

    encoding: str = "utf-8"


@dataclass(frozen=True)
class Array:
    """A LabVIEW array: one I32 size per dimension, then the elements in row-major order."""

    element: Schema
    ndims: int = 1

    def __post_init__(self) -> None:
        if self.ndims < 1:
            raise SchemaError("an array needs at least one dimension")


class Cluster:
    """A LabVIEW cluster: ordered named fields, flattened one after another with no padding."""

    __slots__ = ("fields",)

    def __init__(self, fields: Sequence[tuple[str, Schema]]) -> None:
        self.fields: tuple[tuple[str, Schema], ...] = tuple(fields)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Cluster) and other.fields == self.fields

    def __hash__(self) -> int:
        return hash(self.fields)

    def __repr__(self) -> str:
        return f"Cluster({list(self.fields)!r})"


Schema = (
    IntType
    | FloatType
    | ExtType
    | BoolType
    | BoolArrayType
    | TimestampType
    | String
    | Array
    | Cluster
)

I8 = IntType(8, True)
I16 = IntType(16, True)
I32 = IntType(32, True)
I64 = IntType(64, True)
U8 = IntType(8, False)
U16 = IntType(16, False)
U32 = IntType(32, False)
U64 = IntType(64, False)
SGL = FloatType(False)
DBL = FloatType(True)
EXT = ExtType()
Boolean = BoolType()
BoolArray = BoolArrayType()
Timestamp = TimestampType()
