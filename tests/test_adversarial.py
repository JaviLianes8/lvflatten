"""Hostile input: size headers that lie, output blow-up, deep nesting, and time growth."""

from __future__ import annotations

import time
from collections.abc import Callable

import pytest

from lvflatten import (
    DBL,
    I32,
    Array,
    Bytes,
    Cluster,
    DataError,
    Schema,
    SchemaError,
    String,
    TruncatedDataError,
    format_schema,
    pack,
    parse_schema,
    unpack,
)

_MAX = b"\x7f\xff\xff\xff"


def _timed(action: Callable[[], object]) -> float:
    start = time.perf_counter()
    action()
    return time.perf_counter() - start


def _grows_linearly(small: Callable[[], object], large: Callable[[], object]) -> bool:
    """Four times the input must cost under ten times the time (quadratic would be 16).

    Timing on a shared machine is noisy, so the best of five runs is compared, and the
    comparison is retried a few times before it counts as a failure.
    """
    for _ in range(3):
        best_small = min(_timed(small) for _ in range(5))
        best_large = min(_timed(large) for _ in range(5))
        if best_large < best_small * 10:
            return True
    return False


_TWO_MILLION = (2_000_000).to_bytes(4, "big")


@pytest.mark.parametrize(
    ("schema", "probe", "data"),
    [
        (Array(Cluster([])), _TWO_MILLION, _MAX),
        (Array(I32, 2), _TWO_MILLION + bytes(4), _MAX + bytes(4)),
        (Array(I32, 3), _TWO_MILLION * 2 + bytes(4), _MAX * 2 + bytes(4)),
        (
            Array(Array(Cluster([]))),
            (2).to_bytes(4, "big") + _TWO_MILLION * 2,
            (2).to_bytes(4, "big") + _MAX * 2,
        ),
    ],
    ids=["empty_cluster_elements", "empty_rows_2d", "empty_rows_3d", "nested"],
)
def test_output_blow_up_is_refused_quickly(schema: Schema, probe: bytes, data: bytes) -> None:
    # A bounded probe first: if the budget ever breaks, it builds a few million objects and
    # fails here in seconds, before the 2**31 header could exhaust memory.
    with pytest.raises(DataError):
        unpack(schema, probe)
    start = time.perf_counter()
    with pytest.raises(DataError):
        unpack(schema, data)
    assert time.perf_counter() - start < 0.5


def test_small_empty_shapes_still_decode() -> None:
    assert unpack(Array(I32, 2), b"\x00\x00\x00\x03\x00\x00\x00\x00") == [[], [], []]
    assert unpack(Array(I32, 2), b"\x00\x00\x00\x00\x00\x00\x00\x05") == []
    assert unpack(Array(Cluster([])), b"\x00\x00\x00\x02") == [{}, {}]
    assert pack(Array(I32, 2), [[], [], []]) == b"\x00\x00\x00\x03\x00\x00\x00\x00"


@pytest.mark.parametrize("schema", [String(), Bytes, Array(DBL), Array(I32, 2)])
def test_lying_size_headers_fail_fast(schema: Schema) -> None:
    start = time.perf_counter()
    with pytest.raises(TruncatedDataError):
        unpack(schema, _MAX * 2)
    assert time.perf_counter() - start < 0.5


def test_decoding_time_grows_linearly() -> None:
    def blob(count: int) -> bytes:
        return pack(Array(String()), ["ab"] * count)

    small, large = blob(20_000), blob(80_000)
    assert _grows_linearly(
        lambda: unpack(Array(String()), small), lambda: unpack(Array(String()), large)
    )


def test_parsing_time_grows_linearly() -> None:
    def text(count: int) -> str:
        return "cluster(" + ", ".join(f"f{i}:i32" for i in range(count)) + ")"

    small, large = text(5_000), text(20_000)
    assert _grows_linearly(lambda: parse_schema(small), lambda: parse_schema(large))


def test_text_nesting_limit() -> None:
    assert parse_schema("array(" * 64 + "i32" + ")" * 64) is not None
    with pytest.raises(SchemaError, match="64 levels"):
        parse_schema("array(" * 65 + "i32" + ")" * 65)
    with pytest.raises(SchemaError):
        parse_schema("array(" * 100_000)


def test_programmatic_deep_schemas_raise_schema_error_not_recursion_error() -> None:
    deep: Schema = I32
    for _ in range(5_000):
        deep = Array(deep)
    value: list[object] = []
    for _ in range(4_999):
        value = [value]
    with pytest.raises(SchemaError):
        pack(deep, value)
    with pytest.raises(SchemaError):
        unpack(deep, b"\x00\x00\x00\x01" * 5_000)
    with pytest.raises(SchemaError):
        format_schema(deep)


def test_huge_bogus_tokens_are_not_echoed() -> None:
    with pytest.raises(SchemaError) as info:
        parse_schema("x" * 1_000_000)
    assert len(str(info.value)) < 100
