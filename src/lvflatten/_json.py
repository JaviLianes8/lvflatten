"""Coerce JSON-decoded values into the shapes the codec packs.

JSON has no tuple, so a timestamp arrives as a two-item list while the codec wants an
``LVTimestamp``. Everything else maps straight across, so this only reshapes timestamps,
including those nested inside arrays and clusters.
"""

from __future__ import annotations

from ._errors import SchemaError
from ._schema import Array, Cluster, LVTimestamp, Schema, TimestampType


def from_jsonable(schema: Schema, value: object) -> object:
    """Return ``value`` ready for ``pack``, turning timestamp pairs into ``LVTimestamp``."""
    if isinstance(schema, TimestampType):
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise SchemaError("a timestamp must be a [seconds, fraction] pair")
        return LVTimestamp(value[0], value[1])
    if isinstance(schema, Array):
        if not _reshapes(schema.element):
            return value
        return _map_dims(schema.element, value, schema.ndims)
    if isinstance(schema, Cluster):
        if not isinstance(value, dict):
            raise SchemaError("a cluster value must be a JSON object")
        return {
            name: from_jsonable(sub, value[name]) for name, sub in schema.fields if name in value
        }
    return value


def _map_dims(element: Schema, value: object, depth: int) -> list[object]:
    if not isinstance(value, list):
        raise SchemaError("an array value must be a JSON array")
    if depth == 1:
        return [from_jsonable(element, item) for item in value]
    return [_map_dims(element, row, depth - 1) for row in value]


def _reshapes(schema: Schema) -> bool:
    if isinstance(schema, TimestampType):
        return True
    if isinstance(schema, Array):
        return _reshapes(schema.element)
    if isinstance(schema, Cluster):
        return any(_reshapes(sub) for _, sub in schema.fields)
    return False
