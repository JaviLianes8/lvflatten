"""A compact text form for schemas: parse it to a schema and render it back.

The grammar is small so a schema fits on a command line:

    i32                                 a scalar
    string                              a string (utf-8)
    string(latin-1)                     a string with an explicit encoding
    array(dbl)                          a 1-D array of doubles
    array(i16, 2)                       a 2-D array
    cluster(id:i32, name:string, ok:bool)

Scalar names are case-insensitive: i8..i64, u8..u64, sgl, dbl, ext, bool, boolarray and
timestamp. The form round-trips: ``format_schema(parse_schema(text))`` normalises ``text``.
"""

from __future__ import annotations

from ._errors import SchemaError
from ._schema import (
    DBL,
    EXT,
    I8,
    I16,
    I32,
    I64,
    SGL,
    U8,
    U16,
    U32,
    U64,
    Array,
    BoolArray,
    BoolArrayType,
    Boolean,
    BoolType,
    Cluster,
    ExtType,
    FloatType,
    IntType,
    Schema,
    String,
    Timestamp,
    TimestampType,
)

_SCALARS: dict[str, Schema] = {
    "i8": I8,
    "i16": I16,
    "i32": I32,
    "i64": I64,
    "u8": U8,
    "u16": U16,
    "u32": U32,
    "u64": U64,
    "sgl": SGL,
    "dbl": DBL,
    "ext": EXT,
    "bool": Boolean,
    "boolarray": BoolArray,
    "timestamp": Timestamp,
}

_INT_NAMES = {
    (8, True): "i8",
    (16, True): "i16",
    (32, True): "i32",
    (64, True): "i64",
    (8, False): "u8",
    (16, False): "u16",
    (32, False): "u32",
    (64, False): "u64",
}


def _tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch.isspace():
            i += 1
        elif ch in "(),:":
            tokens.append(ch)
            i += 1
        elif ch.isalnum() or ch in "_-.":
            start = i
            while i < n and (text[i].isalnum() or text[i] in "_-."):
                i += 1
            tokens.append(text[start:i])
        else:
            raise SchemaError(f"unexpected character {ch!r} in schema text")
    return tokens


class _Parser:
    def __init__(self, tokens: list[str]) -> None:
        self._tokens = tokens
        self._pos = 0

    def _peek(self) -> str | None:
        return self._tokens[self._pos] if self._pos < len(self._tokens) else None

    def _next(self) -> str:
        token = self._peek()
        if token is None:
            raise SchemaError("schema text ended early")
        self._pos += 1
        return token

    def _expect(self, token: str) -> None:
        got = self._next()
        if got != token:
            raise SchemaError(f"expected {token!r}, got {got!r}")

    def at_end(self) -> bool:
        return self._pos >= len(self._tokens)

    def parse(self) -> Schema:
        word = self._next()
        key = word.lower()
        if key == "string":
            return self._string()
        if key == "array":
            return self._array()
        if key == "cluster":
            return self._cluster()
        try:
            return _SCALARS[key]
        except KeyError:
            raise SchemaError(f"unknown schema type {word!r}") from None

    def _string(self) -> Schema:
        if self._peek() != "(":
            return String()
        self._next()
        encoding = self._next()
        self._expect(")")
        return String(encoding)

    def _array(self) -> Schema:
        self._expect("(")
        element = self.parse()
        ndims = 1
        if self._peek() == ",":
            self._next()
            ndims = _as_int(self._next())
        self._expect(")")
        return Array(element, ndims)

    def _cluster(self) -> Schema:
        self._expect("(")
        fields: list[tuple[str, Schema]] = []
        if self._peek() != ")":
            fields.append(self._field())
            while self._peek() == ",":
                self._next()
                fields.append(self._field())
        self._expect(")")
        return Cluster(fields)

    def _field(self) -> tuple[str, Schema]:
        name = self._next()
        self._expect(":")
        return name, self.parse()


def _as_int(token: str) -> int:
    try:
        return int(token)
    except ValueError:
        raise SchemaError(f"expected an integer, got {token!r}") from None


def parse_schema(text: str) -> Schema:
    """Build a schema from its compact text form (see this module's grammar)."""
    parser = _Parser(_tokenize(text))
    schema = parser.parse()
    if not parser.at_end():
        raise SchemaError("trailing tokens after the schema")
    return schema


def format_schema(schema: Schema) -> str:
    """Render a schema to the compact text form that ``parse_schema`` reads."""
    if isinstance(schema, IntType):
        return _INT_NAMES[(schema.bits, schema.signed)]
    if isinstance(schema, FloatType):
        return "dbl" if schema.double else "sgl"
    if isinstance(schema, ExtType):
        return "ext"
    if isinstance(schema, BoolType):
        return "bool"
    if isinstance(schema, BoolArrayType):
        return "boolarray"
    if isinstance(schema, TimestampType):
        return "timestamp"
    if isinstance(schema, String):
        return "string" if schema.encoding == "utf-8" else f"string({schema.encoding})"
    if isinstance(schema, Array):
        inner = format_schema(schema.element)
        return f"array({inner})" if schema.ndims == 1 else f"array({inner}, {schema.ndims})"
    if isinstance(schema, Cluster):
        fields = ", ".join(f"{name}:{format_schema(sub)}" for name, sub in schema.fields)
        return f"cluster({fields})"
    raise SchemaError(f"cannot format schema: {schema!r}")  # pragma: no cover - exhaustive above
