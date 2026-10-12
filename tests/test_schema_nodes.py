"""Schema nodes: validation at construction, equality, hashing and readable reprs."""

from __future__ import annotations

import pytest

from lvflatten import (
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
    Bytes,
    Cluster,
    Schema,
    SchemaError,
    String,
    Timestamp,
    pack,
    unpack,
)

_SCALARS = [I8, I16, I32, I64, U8, U16, U32, U64, SGL, DBL, EXT, Boolean, Timestamp, Bytes]
_NAMES = [
    "I8",
    "I16",
    "I32",
    "I64",
    "U8",
    "U16",
    "U32",
    "U64",
    "SGL",
    "DBL",
    "EXT",
    "Boolean",
    "Timestamp",
    "Bytes",
]


@pytest.mark.parametrize(("node", "name"), list(zip(_SCALARS, _NAMES, strict=True)), ids=_NAMES)
def test_scalar_repr_is_its_public_name(node: Schema, name: str) -> None:
    assert repr(node) == name
    assert isinstance(node, Schema)


def test_compound_reprs() -> None:
    assert repr(String()) == "String()"
    assert repr(String("cp1252")) == "String('cp1252')"
    assert repr(Array(DBL)) == "Array(DBL)"
    assert repr(Array(I16, 2)) == "Array(I16, 2)"
    assert repr(Cluster([("a", U8)])) == "Cluster([('a', U8)])"


def test_bool_array_is_an_array_of_booleans() -> None:
    assert BoolArray == Array(Boolean)
    assert pack(BoolArray, [True, False]) == pack(Array(Boolean), [True, False])


def test_bool_array_honours_prepend_size_false() -> None:
    assert pack(BoolArray, [True, False], prepend_size=False) == b"\x01\x00"
    assert unpack(BoolArray, b"\x01\x00", prepend_size=False) == [True, False]


def test_nodes_are_hashable_and_compare_by_value() -> None:
    assert {Array(I32), Array(I32)} == {Array(I32)}
    assert Cluster([("a", I32)]) == Cluster({"a": I32})
    assert hash(Cluster([("a", I32)])) == hash(Cluster({"a": I32}))
    assert Array(I32) != Array(I32, 2)
    assert String() != String("latin-1")


def test_cluster_from_mapping_keeps_order() -> None:
    schema = Cluster({"z": I8, "a": I8})
    assert [name for name, _ in schema.fields] == ["z", "a"]
    assert pack(schema, {"a": 2, "z": 1}) == b"\x01\x02"


def test_cluster_accepts_list_pairs() -> None:
    assert Cluster([["a", I8]]) == Cluster([("a", I8)])  # type: ignore[list-item,unused-ignore]


def test_cluster_is_immutable() -> None:
    schema = Cluster([("a", I8)])
    with pytest.raises(AttributeError):
        schema.fields = ()  # type: ignore[misc,unused-ignore]


@pytest.mark.parametrize(
    "bad",
    [
        [("a", I32), ("a", DBL)],
        [(1, I32)],
        [("a", "i32")],
        [("a",)],
        ["ab"],
    ],
    ids=["duplicate", "non_str_name", "non_schema", "short_pair", "string_pair"],
)
def test_cluster_rejects_bad_fields(bad: list[object]) -> None:
    with pytest.raises(SchemaError):
        Cluster(bad)  # type: ignore[arg-type]


@pytest.mark.parametrize("ndims", [0, -1, True, 1.0, "2"])
def test_array_rejects_bad_dimension_counts(ndims: object) -> None:
    with pytest.raises(SchemaError):
        Array(I32, ndims)  # type: ignore[arg-type]


def test_array_rejects_a_non_schema_element() -> None:
    with pytest.raises(SchemaError):
        Array("i32")  # type: ignore[arg-type]


def test_string_rejects_an_unknown_encoding() -> None:
    with pytest.raises(SchemaError):
        String("no-such-codec")
    with pytest.raises(SchemaError):
        String(8)  # type: ignore[arg-type]


def test_pack_and_unpack_reject_a_non_schema() -> None:
    with pytest.raises(SchemaError):
        pack("i32", 1)  # type: ignore[arg-type]
    with pytest.raises(SchemaError):
        unpack(object(), b"")  # type: ignore[arg-type]


def test_a_subclass_of_schema_that_the_codec_does_not_know_is_refused() -> None:
    class Custom(Schema):
        __slots__ = ()

    with pytest.raises(SchemaError):
        pack(Custom(), 1)
    with pytest.raises(SchemaError):
        unpack(Custom(), b"\x00")
