"""Schema-driven codec for LabVIEW's Flatten To String binary format.

Declare the LabVIEW type with a schema, then ``pack`` a Python value into flattened bytes or
``unpack`` flattened bytes back into a value:

>>> from lvflatten import I32, Cluster, String, pack, unpack
>>> sensor = Cluster([("id", I32), ("label", String())])
>>> blob = pack(sensor, {"id": 7, "label": "probe"})
>>> blob.hex()
'000000070000000570726f6265'
>>> unpack(sensor, blob)
{'id': 7, 'label': 'probe'}
"""

from __future__ import annotations

from ._codec import pack, unpack
from ._compound import Array, BoolArray, Cluster, String
from ._errors import (
    DataError,
    LVFlattenError,
    SchemaError,
    TrailingDataError,
    TruncatedDataError,
)
from ._format import format_schema
from ._lvtime import LVTimestamp
from ._parse import parse_schema
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

__version__ = "1.0.0"

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
    "Bytes",
    "Cluster",
    "DataError",
    "LVFlattenError",
    "LVTimestamp",
    "Schema",
    "SchemaError",
    "String",
    "Timestamp",
    "TrailingDataError",
    "TruncatedDataError",
    "format_schema",
    "pack",
    "parse_schema",
    "unpack",
]
