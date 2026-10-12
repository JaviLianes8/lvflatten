"""Convert between codec values and JSON values, for the command-line tool.

JSON has no tuple and no bytes. A timestamp travels as a ``[seconds, fraction]`` list and
``Bytes`` as a lowercase hex string; everything else maps straight across.
"""

from __future__ import annotations

import binascii

from ._compound import Array, Cluster
from ._errors import SchemaError
from ._lvtime import LVTimestamp
from ._schema import BytesType, Schema, TimestampType


def from_jsonable(schema: Schema, value: object) -> object:
    """Return ``value`` ready for ``pack``: timestamp pairs and hex strings reshaped."""
    if isinstance(schema, TimestampType):
        if not isinstance(value, list) or len(value) != 2:
            raise SchemaError("a timestamp must be a [seconds, fraction] pair")
        return LVTimestamp(value[0], value[1])
    if isinstance(schema, BytesType):
        if not isinstance(value, str):
            raise SchemaError("bytes must be given as a hex string")
        try:
            return binascii.unhexlify("".join(value.split()))
        except (binascii.Error, ValueError):
            raise SchemaError("bytes must be given as a hex string") from None
    if isinstance(schema, Array):
        return _map_dims(schema.element, value, schema.ndims)
    if isinstance(schema, Cluster):
        if not isinstance(value, dict):
            raise SchemaError("a cluster value must be a JSON object")
        return {
            name: from_jsonable(sub, value[name]) for name, sub in schema.fields if name in value
        }
    return value


def to_jsonable(value: object) -> object:
    """Return a decoded value that ``json.dumps`` accepts: bytes become hex strings."""
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, LVTimestamp):
        return [value.seconds, value.fraction]
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    return value


def _map_dims(element: Schema, value: object, depth: int) -> list[object]:
    if not isinstance(value, list):
        raise SchemaError("an array value must be a JSON array")
    if depth == 1:
        return [from_jsonable(element, item) for item in value]
    return [_map_dims(element, row, depth - 1) for row in value]
