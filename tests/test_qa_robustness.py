"""Robustness contracts from the adversarial QA pass: budgets, buffers, limits, pickling."""

from __future__ import annotations

import array
import ctypes
import mmap
import pickle
import time

import pytest

from lvflatten import (
    I8,
    I16,
    I32,
    Array,
    DataError,
    SchemaError,
    TrailingDataError,
    TruncatedDataError,
    pack,
    parse_schema,
    unpack,
    unpack_from,
)


def _count(n: int) -> bytes:
    return n.to_bytes(4, "big")


def test_a_streamed_value_cannot_borrow_the_rest_of_the_buffer_for_its_budget() -> None:
    tail = bytes(100_000)
    rows = _count(1032) + _count(0)
    value, offset = unpack_from(Array(I8, 2), rows + tail)
    assert len(value) == 1032 and offset == 8  # type: ignore[arg-type]
    with pytest.raises(DataError):
        unpack_from(Array(I8, 2), _count(1033) + _count(0) + tail)


def test_walking_hostile_records_builds_at_most_the_floor_per_record() -> None:
    record = _count(1032) + _count(0)
    stream = record * 200
    offset, built = 0, 0
    started = time.perf_counter()
    while offset < len(stream):
        value, offset = unpack_from(Array(I8, 2), stream, offset)
        built += len(value)  # type: ignore[arg-type]
    assert built == 1032 * 200
    assert time.perf_counter() - started < 5
    with pytest.raises(DataError):
        unpack_from(Array(I8, 2), _count(65535) + _count(0) + record * 200)


def test_an_error_does_not_pin_the_callers_bytearray() -> None:
    buf = bytearray(b"\x00\x00")
    try:
        unpack_from(I32, buf)
    except TruncatedDataError:
        buf += b"\x00\x2a"  # growing the buffer while the error is alive must work
    assert unpack_from(I32, buf) == (42, 4)
    caught: list[Exception] = []
    try:
        unpack(I32, bytearray(b"\x00"))
    except TruncatedDataError as exc:
        caught.append(exc)
    assert caught


def test_array_dimensions_are_capped_at_64() -> None:
    assert Array(I32, 64).ndims == 64
    assert parse_schema("array(i32, 64)") == Array(I32, 64)
    with pytest.raises(SchemaError, match="at most 64"):
        Array(I32, 65)
    with pytest.raises(SchemaError, match="at most 64"):
        parse_schema("array(i32, 999999999)")
    with pytest.raises(SchemaError, match="expected a dimension count"):
        parse_schema("array(i32, 1234567890)")


def test_a_huge_dimension_count_in_schema_text_fails_fast() -> None:
    started = time.perf_counter()
    with pytest.raises(SchemaError):
        pack(parse_schema("array(i32, 4000000)"), [])
    assert time.perf_counter() - started < 1


def test_trailing_data_error_survives_pickle() -> None:
    restored = pickle.loads(pickle.dumps(TrailingDataError(3)))
    assert isinstance(restored, TrailingDataError) and restored.count == 3
    assert str(restored) == "3 trailing bytes left after the value"


def test_strided_views_decode_like_their_bytes() -> None:
    view = memoryview(bytes.fromhex("00aa07bb"))[::2]
    assert unpack(I16, view) == 7 == unpack(I16, bytes(view))
    assert unpack_from(I8, view, 1) == (7, 2)


def test_walking_a_strided_view_stays_linear() -> None:
    view = memoryview(bytes(4 * 40_000))[::2]
    started = time.perf_counter()
    offset = 0
    while offset < len(view):
        _, offset = unpack_from(I16, view, offset)
    assert time.perf_counter() - started < 5


def test_any_buffer_protocol_object_is_accepted() -> None:
    raw = bytes.fromhex("0000002a")
    assert unpack(I32, array.array("B", raw)) == 42
    assert unpack_from(I32, (ctypes.c_ubyte * 4)(*raw)) == (42, 4)
    with mmap.mmap(-1, 4) as mapped:
        mapped.write(raw)
        assert unpack(I32, mapped) == 42
        assert unpack_from(I32, mapped) == (42, 4)
    for bad in ("0000002a", 42, None):
        with pytest.raises(TypeError):
            unpack(I32, bad)  # type: ignore[arg-type]


def test_a_list_lying_about_its_length_packs_its_real_items() -> None:
    class Liar(list[int]):
        def __len__(self) -> int:
            return 10**12

    assert pack(Array(I32), Liar([1])) == pack(Array(I32), [1])
