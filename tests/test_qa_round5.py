"""Contracts added after the fifth blind mutation round."""

from __future__ import annotations

import types
from collections.abc import Iterator, Mapping

import pytest

from lvflatten import (
    I8,
    I32,
    Array,
    Cluster,
    DataError,
    SchemaError,
    String,
    pack,
    parse_schema,
    unpack,
    unpack_from,
)
from lvflatten._schema import Schema


def test_unpack_from_refuses_a_too_deep_schema_cleanly() -> None:
    deep: Schema = I8
    for _ in range(3000):
        deep = Array(deep)
    data = bytes.fromhex("00000001") * 3000 + b"\x07"
    with pytest.raises(SchemaError, match="nests too deeply"):
        unpack_from(deep, data)


def test_a_cluster_needs_commas_between_fields() -> None:
    with pytest.raises(SchemaError):
        parse_schema("cluster(a:i32 b:i32)")


class _Fields(Mapping[str, object]):
    def __init__(self, data: dict[str, object]) -> None:
        self._data = data

    def __getitem__(self, key: str) -> object:
        return self._data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)


def test_a_cluster_packs_from_any_mapping() -> None:
    schema = Cluster([("a", I8), ("b", I8)])
    expected = pack(schema, {"a": 1, "b": 2})
    assert pack(schema, types.MappingProxyType({"a": 1, "b": 2})) == expected
    assert pack(schema, _Fields({"a": 1, "b": 2})) == expected


@pytest.mark.parametrize("order", [["big"], {"big": 1}, None, 1])
def test_a_bad_byte_order_is_a_schema_error_everywhere(order: object) -> None:
    with pytest.raises(SchemaError, match="byte_order"):
        pack(I32, 1, byte_order=order)  # type: ignore[arg-type]
    with pytest.raises(SchemaError, match="byte_order"):
        unpack(I32, bytes(4), byte_order=order)  # type: ignore[arg-type]
    with pytest.raises(SchemaError, match="byte_order"):
        unpack_from(I32, bytes(4), byte_order=order)  # type: ignore[arg-type]


def test_undecodable_text_names_the_offset_of_the_first_bad_byte() -> None:
    with pytest.raises(DataError, match=r"offset 2\)"):
        unpack(String(), bytes.fromhex("00000003") + b"ab\xff")


@pytest.mark.parametrize(
    ("schema", "hex_bytes"),
    [
        (Array(I8, 2), "001e848000000000"),  # 2,000,000 empty rows from 8 bytes
        (Array(Cluster([])), "001e8480"),  # 2,000,000 empty clusters from 4 bytes
        (Array(Cluster([("x", Cluster([]))])), "000f4240"),  # 1,000,000 x 2 dicts
    ],
)
def test_empty_shapes_far_over_the_budget_are_refused_before_building(
    schema: Schema, hex_bytes: str
) -> None:
    with pytest.raises(DataError):
        unpack(schema, bytes.fromhex(hex_bytes))
    with pytest.raises(DataError):
        unpack_from(schema, bytes.fromhex(hex_bytes))
