"""Byte sizes of fixed-size schemas, used to bound and pre-check array reads."""

from __future__ import annotations

from ._compound import Cluster
from ._schema import BoolType, ExtType, FloatType, IntType, Schema, TimestampType


def fixed_size(schema: Schema) -> int | None:
    """Byte size of a fixed-size schema, or None if it carries a length of its own."""
    if isinstance(schema, IntType):
        return schema.bits // 8
    if isinstance(schema, FloatType):
        return 8 if schema.double else 4
    if isinstance(schema, (ExtType, TimestampType)):
        return 16
    if isinstance(schema, BoolType):
        return 1
    if isinstance(schema, Cluster):
        total = 0
        for _, field_schema in schema.fields:
            size = fixed_size(field_schema)
            if size is None:
                return None
            total += size
        return total
    return None
