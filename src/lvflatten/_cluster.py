"""Pack and unpack LabVIEW clusters (ordered named fields, no padding)."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from ._errors import SchemaError
from ._reader import Reader
from ._schema import Cluster, Schema

PackNode = Callable[[Schema, object, str, bytearray], None]
UnpackNode = Callable[[Schema, Reader, str], object]


def pack_cluster(
    schema: Cluster, value: object, bo: str, out: bytearray, pack_node: PackNode
) -> None:
    if not isinstance(value, Mapping):
        raise SchemaError("expected a mapping of field name to value for a cluster")
    for name, field_schema in schema.fields:
        if name not in value:
            raise SchemaError(f"cluster value is missing field {name!r}")
        pack_node(field_schema, value[name], bo, out)


def unpack_cluster(
    schema: Cluster, reader: Reader, bo: str, unpack_node: UnpackNode
) -> dict[str, object]:
    result: dict[str, object] = {}
    for name, field_schema in schema.fields:
        result[name] = unpack_node(field_schema, reader, bo)
    return result
