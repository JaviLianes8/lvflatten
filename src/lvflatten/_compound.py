"""The schema nodes built for the shape at hand: ``String``, ``Array`` and ``Cluster``."""

from __future__ import annotations

import codecs
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from ._errors import SchemaError, short
from ._schema import Boolean, Schema


@dataclass(frozen=True, repr=False)
class String(Schema):
    """A LabVIEW string: an I32 byte count followed by the encoded text.

    ``encoding`` is any Python codec name and is checked when the node is built. LabVIEW on
    Windows writes text in the system ANSI code page, so ``String("cp1252")`` is the usual
    choice for non-ASCII text from a Western Windows machine. Use ``Bytes`` for binary data.

    >>> from lvflatten import String, pack, unpack
    >>> pack(String(), "ABC").hex()
    '00000003414243'
    >>> unpack(String("cp1252"), bytes.fromhex("00000001e9"))
    'é'
    """

    encoding: str = "utf-8"

    def __post_init__(self) -> None:
        if not isinstance(self.encoding, str):
            raise SchemaError("a string encoding must be a codec name")
        try:
            codecs.lookup(self.encoding)
        except LookupError:
            raise SchemaError(f"unknown text encoding {short(self.encoding)}") from None

    def __repr__(self) -> str:
        return "String()" if self.encoding == "utf-8" else f"String({self.encoding!r})"


@dataclass(frozen=True, repr=False)
class Array(Schema):
    """A LabVIEW array: one I32 size per dimension, then the elements in row-major order.

    The value is a list (nested ``ndims`` deep) or a tuple; rows must be rectangular, and
    unpack always returns lists. ``BoolArray`` is a ready-made ``Array(Boolean)``.

    >>> from lvflatten import I8, Array, pack
    >>> pack(Array(I8, 2), [[1, 2, 3], [4, 5, 6]]).hex()
    '0000000200000003010203040506'
    >>> from lvflatten import Boolean, BoolArray
    >>> BoolArray == Array(Boolean), pack(BoolArray, [True, False]).hex()
    (True, '000000020100')
    """

    element: Schema
    ndims: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.element, Schema):
            raise SchemaError(f"an array element must be a schema, got {short(self.element)}")
        if isinstance(self.ndims, bool) or not isinstance(self.ndims, int) or self.ndims < 1:
            raise SchemaError("an array needs a whole number of dimensions, at least one")

    def __repr__(self) -> str:
        if self.ndims == 1:
            return f"Array({self.element!r})"
        return f"Array({self.element!r}, {self.ndims})"


class Cluster(Schema):
    """A LabVIEW cluster: ordered named fields, flattened one after another with no padding.

    Build it from ``(name, schema)`` pairs or from a dict (which keeps insertion order).
    Field names must be unique strings. The value is a mapping from field name to value;
    unpack returns a ``dict`` in field order.

    >>> from lvflatten import I16, I32, Cluster, pack
    >>> pack(Cluster({"a": I16, "b": I32}), {"a": 4, "b": 12}).hex()
    '00040000000c'
    """

    __slots__ = ("fields",)

    fields: tuple[tuple[str, Schema], ...]

    def __init__(self, fields: Mapping[str, Schema] | Iterable[tuple[str, Schema]]) -> None:
        raw = list(fields.items()) if isinstance(fields, Mapping) else list(fields)
        pairs: list[tuple[str, Schema]] = []
        seen: set[str] = set()
        for pair in raw:
            if not isinstance(pair, (tuple, list)) or len(pair) != 2:
                raise SchemaError("cluster fields must be (name, schema) pairs")
            name, schema = pair
            if not isinstance(name, str):
                raise SchemaError(f"a cluster field name must be a str, got {short(name)}")
            if not isinstance(schema, Schema):
                raise SchemaError(f"field {short(name)} needs a schema, got {short(schema)}")
            if name in seen:
                raise SchemaError(f"duplicate cluster field name {short(name)}")
            seen.add(name)
            pairs.append((name, schema))
        object.__setattr__(self, "fields", tuple(pairs))

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("Cluster is immutable")

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Cluster) and other.fields == self.fields

    def __hash__(self) -> int:
        return hash(self.fields)

    def __repr__(self) -> str:
        return f"Cluster({list(self.fields)!r})"


BoolArray = Array(Boolean)
