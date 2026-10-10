import pytest

from lvflatten import DBL, I32, Array, Boolean, Cluster, SchemaError, String, pack, unpack


def test_cluster_round_trips() -> None:
    schema = Cluster([("id", I32), ("name", String()), ("ok", Boolean)])
    value = {"id": 42, "name": "probe", "ok": True}
    assert unpack(schema, pack(schema, value)) == value


def test_cluster_keeps_field_order_with_no_padding() -> None:
    schema = Cluster([("a", I32), ("b", I32)])
    assert pack(schema, {"a": 1, "b": 2}) == b"\x00\x00\x00\x01\x00\x00\x00\x02"


def test_nested_cluster_round_trips() -> None:
    inner = Cluster([("x", DBL), ("y", DBL)])
    schema = Cluster([("point", inner), ("tags", Array(String()))])
    value = {"point": {"x": 1.5, "y": -2.5}, "tags": ["a", "b"]}
    assert unpack(schema, pack(schema, value)) == value


def test_cluster_missing_field_raises() -> None:
    schema = Cluster([("a", I32), ("b", I32)])
    with pytest.raises(SchemaError):
        pack(schema, {"a": 1})


def test_cluster_rejects_non_mapping() -> None:
    schema = Cluster([("a", I32)])
    with pytest.raises(SchemaError):
        pack(schema, [1])


def test_cluster_schema_is_hashable_and_comparable() -> None:
    first = Cluster([("a", I32)])
    second = Cluster([("a", I32)])
    assert first == second
    assert hash(first) == hash(second)
