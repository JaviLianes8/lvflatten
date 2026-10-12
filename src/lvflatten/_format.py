"""Render a schema back to the compact text form that ``parse_schema`` reads.

This is the inverse of ``parse_schema``: ``parse_schema(format_schema(s)) == s`` for every
schema, and ``format_schema(parse_schema(text))`` normalises ``text``.
"""

from __future__ import annotations

from ._compound import Array, Cluster, String
from ._errors import SchemaError, short
from ._parse import is_bare
from ._schema import BoolType, BytesType, ExtType, FloatType, IntType, Schema, TimestampType


def _name(text: str) -> str:
    if is_bare(text):
        return text
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def format_schema(schema: Schema) -> str:
    """Render a schema to the compact text form that ``parse_schema`` reads.

    Raises :class:`SchemaError` for anything that is not a schema node.

    >>> from lvflatten import DBL, I32, Array, BoolArray, Cluster, format_schema
    >>> format_schema(Cluster([("Error Code", I32), ("grid", Array(DBL, 2)), ("f", BoolArray)]))
    'cluster("Error Code":i32, grid:array(dbl, 2), f:array(bool))'
    """
    if isinstance(schema, (IntType, FloatType, ExtType)):
        return repr(schema).lower()
    if isinstance(schema, BoolType):
        return "bool"
    if isinstance(schema, TimestampType):
        return "timestamp"
    if isinstance(schema, BytesType):
        return "bytes"
    if isinstance(schema, String):
        return "string" if schema.encoding == "utf-8" else f"string({_name(schema.encoding)})"
    if isinstance(schema, Array):
        inner = format_schema(schema.element)
        return f"array({inner})" if schema.ndims == 1 else f"array({inner}, {schema.ndims})"
    if isinstance(schema, Cluster):
        fields = ", ".join(f"{_name(name)}:{format_schema(sub)}" for name, sub in schema.fields)
        return f"cluster({fields})"
    raise SchemaError(f"cannot format {short(schema)}: not a schema node")
