"""A compact text form for schemas: parse it to a schema (``format_schema`` renders it back).

The grammar is small so a schema fits on a command line::

    i32                                 a scalar
    string                              a string (utf-8)
    string(cp1252)                      a string with an explicit encoding
    bytes                               a string holding binary data
    array(dbl)                          a 1-D array of doubles
    array(i16, 2)                       a 2-D array
    cluster(id:i32, name:string, ok:bool)
    cluster("Error Code":i32)           a field name with spaces, in double quotes

Type names are case-insensitive: i8..i64, u8..u64, sgl, dbl, ext, bool, boolarray,
timestamp, bytes, string, array and cluster. A bare field name is letters, digits, ``_``,
``-`` and ``.``; any other name goes in double quotes, where a backslash escapes ``"`` or
another backslash. Nesting deeper than 64 levels is refused.
"""

from __future__ import annotations

from ._compound import Array, BoolArray, Cluster, String
from ._errors import SchemaError, short
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
    Boolean,
    Bytes,
    Schema,
    Timestamp,
)

MAX_DEPTH = 64
_PUNCT = "(),:"
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
    "bytes": Bytes,
}


def is_bare(text: str) -> bool:
    """True when ``text`` can be written without quotes in the schema text form."""
    return bool(text) and all(ch.isalnum() or ch in "_-." for ch in text)


def _quoted(text: str, start: int) -> tuple[str, int]:
    out: list[str] = []
    i = start + 1
    while i < len(text):
        ch = text[i]
        if ch == '"':
            return "".join(out), i + 1
        if ch == "\\":
            i += 1
            if i >= len(text) or text[i] not in '"\\':
                raise SchemaError("a backslash in a quoted name must escape '\"' or '\\'")
            ch = text[i]
        out.append(ch)
        i += 1
    raise SchemaError("unterminated quoted name in schema text")


def _tokenize(text: str) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch.isspace():
            i += 1
        elif ch in _PUNCT:
            tokens.append(("punct", ch))
            i += 1
        elif ch == '"':
            word, i = _quoted(text, i)
            tokens.append(("quoted", word))
        elif ch.isalnum() or ch in "_-.":
            start = i
            while i < n and (text[i].isalnum() or text[i] in "_-."):
                i += 1
            tokens.append(("word", text[start:i]))
        else:
            raise SchemaError(f"unexpected character {short(ch)} at offset {i} in schema text")
    return tokens


class _Parser:
    def __init__(self, tokens: list[tuple[str, str]]) -> None:
        self._tokens = tokens
        self._pos = 0

    def peek(self) -> str | None:
        if self._pos < len(self._tokens) and self._tokens[self._pos][0] == "punct":
            return self._tokens[self._pos][1]
        return None

    def take(self, kinds: tuple[str, ...] = ("word", "quoted")) -> str:
        if self._pos >= len(self._tokens):
            raise SchemaError("schema text ended early")
        kind, text = self._tokens[self._pos]
        if kind not in kinds:
            raise SchemaError(f"unexpected {short(text)} in schema text")
        self._pos += 1
        return text

    def expect(self, punct: str) -> None:
        if self.take(("punct",)) != punct:
            raise SchemaError(f"expected {punct!r} in schema text")

    def at_end(self) -> bool:
        return self._pos >= len(self._tokens)

    def parse(self, depth: int = 0) -> Schema:
        if depth > MAX_DEPTH:
            raise SchemaError(f"schema text nests deeper than {MAX_DEPTH} levels")
        word = self.take(("word",))
        key = word.lower()
        if key == "string":
            if self.peek() != "(":
                return String()
            self.expect("(")
            encoding = self.take()
            self.expect(")")
            return String(encoding)
        if key == "array":
            self.expect("(")
            element = self.parse(depth + 1)
            ndims = 1
            if self.peek() == ",":
                self.expect(",")
                ndims = _as_int(self.take(("word",)))
            self.expect(")")
            return Array(element, ndims)
        if key == "cluster":
            return self._cluster(depth)
        if key not in _SCALARS:
            raise SchemaError(f"unknown schema type {short(word)}")
        return _SCALARS[key]

    def _cluster(self, depth: int) -> Schema:
        self.expect("(")
        fields: list[tuple[str, Schema]] = []
        while self.peek() != ")":
            if fields:
                self.expect(",")
            name = self.take()
            self.expect(":")
            fields.append((name, self.parse(depth + 1)))
        self.expect(")")
        return Cluster(fields)


def _as_int(token: str) -> int:
    if not token.isdigit() or not token.isascii() or len(token) > 9:
        raise SchemaError(f"expected a dimension count, got {short(token)}")
    return int(token)


def parse_schema(text: str) -> Schema:
    """Build a schema from its compact text form (grammar in the module docstring).

    Raises :class:`SchemaError` for text that does not follow the grammar.

    >>> from lvflatten import parse_schema
    >>> parse_schema('cluster(id:i32, tags:array(string), "Error Code":i32)')
    Cluster([('id', I32), ('tags', Array(String())), ('Error Code', I32)])
    """
    if not isinstance(text, str):
        raise SchemaError(f"schema text must be a str, got {type(text).__name__}")
    parser = _Parser(_tokenize(text))
    schema = parser.parse()
    if not parser.at_end():
        raise SchemaError("trailing tokens after the schema")
    return schema
