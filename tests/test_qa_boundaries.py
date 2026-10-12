"""Boundary contracts added after the second blind mutation round."""

from __future__ import annotations

import array

import pytest
from _cli_command import run_cli

from lvflatten import (
    I8,
    U16,
    U32,
    Array,
    Cluster,
    DataError,
    LVTimestamp,
    String,
    pack,
    unpack,
    unpack_from,
)


def test_a_two_dimensional_strided_byte_view_decodes_like_its_bytes() -> None:
    view = memoryview(bytes([0, 9, 0, 9, 0, 9, 2, 9, 7, 9, 8, 9])).cast("B", (6, 2))[::2]
    flat = bytes(view)
    assert unpack(U32, view[:2]) == unpack(U32, bytes(view[:2]))
    assert unpack_from(U16, view, 0) == unpack_from(U16, flat, 0) == (9, 2)
    assert unpack(Array(I8), bytes.fromhex("00000006") + flat) == list(flat)


@pytest.mark.parametrize("typecode", ["H", "d"])
def test_a_strided_view_of_wide_items_decodes_like_its_bytes(typecode: str) -> None:
    items = [0x0102, 0xAAAA, 0x0304, 0xBBBB] if typecode == "H" else [1.5, 2.0, -3.25, 4.0]
    view = memoryview(array.array(typecode, items))[::2]
    flat = bytes(view)
    assert unpack(Array(I8), len(flat).to_bytes(4, "big") + flat) == [
        b - 256 if b > 127 else b for b in flat
    ]
    assert unpack_from(U16, view, 2) == unpack_from(U16, flat, 2)
    assert unpack_from(U16, view, 2)[1] == 4  # offsets count bytes, not items


def test_a_value_at_an_offset_does_not_borrow_the_bytes_before_it() -> None:
    prefix = bytes(5000)
    with pytest.raises(DataError):
        unpack_from(Array(Cluster([])), prefix + (1029).to_bytes(4, "big"), 5000)
    value, offset = unpack_from(Array(Cluster([])), prefix + (1028).to_bytes(4, "big"), 5000)
    assert len(value) == 1028 and offset == 5004  # type: ignore[arg-type]


def test_to_datetime_rounds_a_microsecond_tie_up() -> None:
    tie = 1 << 57  # exactly 7812.5 microseconds
    assert LVTimestamp(0, tie).to_datetime().microsecond == 7813
    assert LVTimestamp(0, tie - 1).to_datetime().microsecond == 7812
    assert LVTimestamp(0, tie + 1).to_datetime().microsecond == 7813


@pytest.mark.parametrize(
    ("schema_text", "json_text", "schema", "value"),
    [
        ("string", '"ab"', String(), "ab"),
        ("array(i8)", "[1, -2]", Array(I8), [1, -2]),
    ],
)
def test_cli_flatten_no_size_drops_the_size(
    schema_text: str, json_text: str, schema: object, value: object
) -> None:
    result = run_cli("flatten", "-s", schema_text, "-j", json_text, "--no-size")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == pack(schema, value, prepend_size=False).hex()  # type: ignore[arg-type]


@pytest.mark.parametrize("json_text", ["[1]", "[1, 2, 3]", "{}"])
def test_cli_time_stamp_must_be_a_pair(json_text: str) -> None:
    result = run_cli("flatten", "-s", "timestamp", "-j", json_text)
    assert result.returncode == 1
    assert "a timestamp must be a [seconds, fraction] pair" in result.stderr


def test_messages_about_huge_declared_counts_stay_short() -> None:
    from lvflatten import U8, TruncatedDataError

    huge = (0x7FFFFFFF).to_bytes(4, "big")
    with pytest.raises(TruncatedDataError) as truncated:
        unpack(Array(U8, 64), huge * 64)
    assert "more than 2**63" in str(truncated.value) and len(str(truncated.value)) < 120
    with pytest.raises(DataError) as empty:
        unpack(Array(U8, 64), huge * 63 + bytes(4))
    assert "more than 2**63" in str(empty.value) and len(str(empty.value)) < 120
    with pytest.raises(TruncatedDataError, match="declares 3 elements"):
        unpack(Array(U8), bytes.fromhex("00000003"))


def test_a_bytes_subclass_is_read_through_the_buffer_protocol() -> None:
    from lvflatten import I32

    class Odd(bytes):
        def __getitem__(self, key: object) -> bytes:  # type: ignore[override]
            return b""

    assert unpack_from(I32, Odd(b"\x00\x00\x00\x01")) == (1, 4)
    assert unpack(I32, Odd(b"\x00\x00\x00\x01")) == 1


def test_shapes_beyond_the_free_budget_pack_but_are_refused_on_unpack() -> None:
    from lvflatten import I32

    small: list[list[int]] = [[]] * 1000
    large: list[list[int]] = [[]] * 2000
    assert unpack(Array(I32, 2), pack(Array(I32, 2), small)) == small
    with pytest.raises(DataError):
        unpack(Array(I32, 2), pack(Array(I32, 2), large))
    with pytest.raises(DataError):
        unpack(Array(Cluster([])), pack(Array(Cluster([])), [{}] * 2000))
