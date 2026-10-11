"""Render a schema back to the compact text form that ``parse_schema`` reads.

This is the inverse of ``parse_schema`` in ``_parse``: ``format_schema(parse_schema(text))``
normalises ``text``. It lives in its own module so the parser stays small.
"""

from __future__ import annotations

from ._errors import SchemaError
from ._schema import (
    Array,
    BoolArrayType,
    BoolType,
    Cluster,
    ExtType,
    FloatType,
    IntType,
    Schema,
    String,
    TimestampType,
)

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
