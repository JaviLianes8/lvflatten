"""Schema-driven codec for LabVIEW's Flatten To String binary format."""

from __future__ import annotations

from ._codec import pack, unpack
from ._errors import LVFlattenError, SchemaError, TruncatedDataError
from ._parse import format_schema, parse_schema
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
    Boolean,
    Cluster,
    LVTimestamp,
    Schema,
    String,
    Timestamp,
)

__version__ = "0.2.0"

__all__ = [
    "DBL",
    "EXT",
    "I8",
    "I16",
    "I32",
    "I64",
    "SGL",
    "U8",
    "U16",
    "U32",
    "U64",
    "Array",
    "BoolArray",
    "Boolean",
    "Cluster",
    "LVFlattenError",
    "LVTimestamp",
    "Schema",
    "SchemaError",
    "String",
    "Timestamp",
    "TruncatedDataError",
    "format_schema",
    "pack",
    "parse_schema",
    "unpack",
]
