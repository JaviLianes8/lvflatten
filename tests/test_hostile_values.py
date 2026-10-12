"""Contracts from the adversarial review: hostile values, copies, views and memory bounds."""

from __future__ import annotations

import copy
import pickle
import struct
import time
import tracemalloc

import pytest

from lvflatten import (
    DBL,
    EXT,
    I8,
    I16,
    I32,
    Array,
    Cluster,
    DataError,
    LVFlattenError,
    SchemaError,
    String,
    pack,
    unpack,
    unpack_from,
)


class _LyingList(list[object]):
    def __len__(self) -> int:
        return 5


class _BadStr(str):
    def encode(self, encoding: str = "utf-8", errors: str = "strict") -> bytes:
        return "not bytes"  # type: ignore[return-value]


class _BadFloat(float):
    def __float__(self) -> float:
        return "x"  # type: ignore[return-value]


class _LyingDict(dict[str, object]):
    def __contains__(self, key: object) -> bool:
        return True


def test_a_list_that_lies_about_its_length_cannot_corrupt_the_output() -> None:
    blob = pack(Array(I8), _LyingList([1, 2]))
    assert blob == b"\x00\x00\x00\x02\x01\x02"


@pytest.mark.parametrize(
    ("schema", "value"),
    [
        (String(), _BadStr("a")),
        (DBL, _BadFloat(1.0)),
        (EXT, _BadFloat(1.0)),
        (Cluster([("a", I32)]), _LyingDict()),
    ],
    ids=["str_encode", "float_dbl", "float_ext", "dict_contains"],
)
def test_hostile_subclasses_raise_schema_error(schema: object, value: object) -> None:
    with pytest.raises(SchemaError):
        pack(schema, value)  # type: ignore[arg-type]


@pytest.mark.parametrize("fields", [5, None, 1.5])
def test_cluster_with_non_iterable_fields_is_a_schema_error(fields: object) -> None:
    with pytest.raises(SchemaError):
        Cluster(fields)  # type: ignore[arg-type]


def test_schemas_copy_and_pickle() -> None:
    schema = Array(Cluster([("a", I32), ("inner", Cluster({"s": String("cp1252")}))]), 2)
    assert copy.copy(schema) == schema
    assert copy.deepcopy(schema) == schema
    assert pickle.loads(pickle.dumps(schema)) == schema


def test_a_released_memoryview_is_a_type_error() -> None:
    view = memoryview(b"\x00\x00\x00\x01")
    view.release()
    with pytest.raises(TypeError):
        unpack(I32, view)
    with pytest.raises(TypeError):
        unpack_from(I32, view)


def test_non_byte_views_are_read_as_their_raw_bytes() -> None:
    words = memoryview(struct.pack(">2H", 1, 2)).cast("H")
    assert unpack_from(I16, words) == (1, 2)
    assert unpack(Array(I16), memoryview(b"\x00\x00\x00\x01\x00\x07")[::1]) == [7]


def test_walking_a_bytearray_with_unpack_from_is_linear() -> None:
    def walk(count: int) -> float:
        buffer = bytearray(b"\x00\x01" * count)
        start, offset = time.perf_counter(), 0
        while offset < len(buffer):
            _, offset = unpack_from(I16, buffer, offset)
        return time.perf_counter() - start

    small = min(walk(20_000) for _ in range(3))
    large = min(walk(80_000) for _ in range(3))
    assert large < small * 10


@pytest.mark.parametrize("depth", [2, 8, 32])
def test_nested_empty_clusters_cannot_amplify_memory(depth: int) -> None:
    element = Cluster([])
    for _ in range(depth - 1):
        element = Cluster([("x", element)])
    data = (20_000).to_bytes(4, "big") + bytes(5_000)  # claims far more than it holds
    tracemalloc.start()
    try:
        with pytest.raises(DataError):
            unpack(Array(element), data)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 2_000_000


def test_only_documented_errors_escape_for_hostile_subclasses_of_bytes() -> None:
    class Weird(bytes):
        pass

    with pytest.raises(LVFlattenError):
        unpack(I32, Weird(b"\x00"))
