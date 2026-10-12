"""Render a schema back to the compact text form that ``parse_schema`` reads.

This is the inverse of ``parse_schema``: ``parse_schema(format_schema(s)) == s`` for every
schema the text form can hold (nesting up to 64 levels), and ``format_schema(parse_schema(t))``
normalises ``t``.
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

    Raises :class:`SchemaError` for anything that is not a schema node, or for a schema
    nested too deeply for Python's recursion limit.

    >>> from lvflatten import DBL, I32, Array, BoolArray, Cluster, format_schema
    >>> format_schema(Cluster([("Error Code", I32), ("grid", Array(DBL, 2)), ("f", BoolArray)]))
    'cluster("Error Code":i32, grid:array(dbl, 2), f:array(bool))'
    """
    try:
        return _format(schema)
    except RecursionError:
        raise SchemaError("the schema nests too deeply to format") from None


def _format(schema: Schema) -> str:
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
        inner = _format(schema.element)
        return f"array({inner})" if schema.ndims == 1 else f"array({inner}, {schema.ndims})"
    if isinstance(schema, Cluster):
        fields = ", ".join(f"{_name(name)}:{_format(sub)}" for name, sub in schema.fields)
        return f"cluster({fields})"
    raise SchemaError(f"cannot format {short(schema)}: not a schema node")
