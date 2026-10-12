"""The schema base class and the fixed-size scalar nodes.

Flattened data carries no type information, so every pack or unpack needs a schema node to
say how the bytes should be read. The scalars are ready-made singletons (``I32``, ``DBL``,
``EXT``, ``Boolean``, ``Timestamp``, ``Bytes``, ...); ``String``, ``Array`` and ``Cluster``
in ``_compound`` are built for the shape at hand.
"""

from __future__ import annotations

from dataclasses import dataclass

from ._errors import SchemaError, short


class Schema:
    """Base class of every schema node; use it to annotate or test for "any schema".

    >>> from lvflatten import I32, Array, Schema
    >>> isinstance(I32, Schema), isinstance(Array(I32), Schema)
    (True, True)
    """

    __slots__ = ()


_INT_NAMES = {
    (8, True): "I8",
    (16, True): "I16",
    (32, True): "I32",
    (64, True): "I64",
    (8, False): "U8",
    (16, False): "U16",
    (32, False): "U32",
    (64, False): "U64",
}


@dataclass(frozen=True, repr=False)
class IntType(Schema):
    """A fixed-width integer: ``I8 I16 I32 I64`` signed, ``U8 U16 U32 U64`` unsigned.

    The value is a Python ``int`` (``bool`` is refused) and must fit the width.

    >>> from lvflatten import I16, U32, pack, unpack
    >>> pack(I16, -2)
    b'\\xff\\xfe'
    >>> unpack(U32, b"\\xde\\xad\\xbe\\xef") == 0xDEADBEEF
    True
    """

    bits: int
    signed: bool

    def __post_init__(self) -> None:
        if (self.bits, self.signed) not in _INT_NAMES:
            raise SchemaError(f"unsupported integer width: {short(self.bits)}")

    def __repr__(self) -> str:
        return _INT_NAMES[(self.bits, self.signed)]


@dataclass(frozen=True, repr=False)
class FloatType(Schema):
    """An IEEE 754 float: ``SGL`` (4 bytes) or ``DBL`` (8 bytes); the value is a ``float``.

    >>> from lvflatten import DBL, SGL, pack
    >>> pack(DBL, 0.25).hex()
    '3fd0000000000000'
    >>> pack(SGL, 1.0).hex()
    '3f800000'
    """

    double: bool

    def __repr__(self) -> str:
        return "DBL" if self.double else "SGL"


class _Singleton(Schema):
    """A node with no parameters: all instances are equal and it reprs as its public name."""

    __slots__ = ()
    _name = ""

    def __eq__(self, other: object) -> bool:
        return type(other) is type(self)

    def __hash__(self) -> int:
        return hash(type(self).__name__)

    def __repr__(self) -> str:
        return self._name


class ExtType(_Singleton):
    """``EXT``: an extended float, 80-bit x87 format held big-endian in a 16-byte field.

    Values a Python ``float`` can hold round-trip exactly; wider ones are rounded.

    >>> from lvflatten import EXT, pack, unpack
    >>> pack(EXT, 1.0).hex()
    '3fff8000000000000000000000000000'
    >>> unpack(EXT, pack(EXT, -2.5))
    -2.5
    """

    __slots__ = ()
    _name = "EXT"


class BoolType(_Singleton):
    """``Boolean``: one byte, ``01`` for TRUE and ``00`` for FALSE; any nonzero byte reads TRUE.

    >>> from lvflatten import Boolean, pack, unpack
    >>> pack(Boolean, True), unpack(Boolean, b"\\x07")
    (b'\\x01', True)
    """

    __slots__ = ()
    _name = "Boolean"


class TimestampType(_Singleton):
    """``Timestamp``: the 128-bit time stamp, I64 seconds then U64 fraction since 1904.

    The value is an :class:`LVTimestamp`.

    >>> from lvflatten import LVTimestamp, Timestamp, pack
    >>> pack(Timestamp, LVTimestamp(1, 1 << 63)).hex()
    '00000000000000018000000000000000'
    """

    __slots__ = ()
    _name = "Timestamp"


class BytesType(_Singleton):
    """``Bytes``: a LabVIEW string holding binary data, read and written as ``bytes``.

    The wire form is the same as :class:`String` (an I32 byte count then the bytes) and also
    the same as an ``Array(U8)``, but no text decoding is attempted.

    >>> from lvflatten import Bytes, pack, unpack
    >>> pack(Bytes, b"\\xff\\x00").hex()
    '00000002ff00'
    >>> unpack(Bytes, bytes.fromhex("00000001ff"))
    b'\\xff'
    """

    __slots__ = ()
    _name = "Bytes"


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
Timestamp = TimestampType()
Bytes = BytesType()
