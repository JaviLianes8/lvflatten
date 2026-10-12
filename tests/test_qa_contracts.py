"""Boundary contracts added after the blind mutation round of the contract-strength QA pass."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

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
    DataError,
    LVFlattenError,
    LVTimestamp,
    SchemaError,
    String,
    Timestamp,
    TrailingDataError,
    TruncatedDataError,
    pack,
    unpack,
)
from lvflatten._errors import short
from lvflatten._sizes import fixed_size
from lvflatten._string import _write


@pytest.mark.parametrize(
    "hex_bytes",
    ["7fff0000000000000000000000000001", "7fff8000000000000000000000000000"],
)
def test_every_nonzero_ext_fraction_under_a_full_exponent_is_nan(hex_bytes: str) -> None:
    for sign_bit in (0, 0x80):
        raw = bytes([int(hex_bytes[:2], 16) | sign_bit]) + bytes.fromhex(hex_bytes[2:])
        value = unpack(EXT, raw)
        assert isinstance(value, float) and math.isnan(value)
        assert math.copysign(1.0, value) == (-1.0 if sign_bit else 1.0)


@pytest.mark.parametrize("micro", [1, 3, 999_999])
def test_from_datetime_takes_the_fraction_just_below(micro: int) -> None:
    epoch = datetime(1904, 1, 1, tzinfo=timezone.utc)
    stamp = LVTimestamp.from_datetime(epoch + timedelta(microseconds=micro))
    assert stamp == LVTimestamp(0, micro * 2**64 // 10**6)


def test_from_datetime_of_one_microsecond_is_exact() -> None:
    moment = datetime(1904, 1, 1, 0, 0, 0, 1, tzinfo=timezone.utc)
    assert LVTimestamp.from_datetime(moment) == LVTimestamp(0, 18446744073709)


class _Sized(bytes):
    """Bytes that report a length, to reach the I32 limit without allocating 2 GiB."""

    claimed = 0

    def __len__(self) -> int:
        return self.claimed


def test_string_length_limit_is_exactly_i32_max() -> None:
    at_limit, over = _Sized(b""), _Sized(b"")
    at_limit.claimed, over.claimed = 0x7FFFFFFF, 0x80000000
    out = bytearray()
    _write(at_limit, ">", out)
    assert out == bytes.fromhex("7fffffff")
    with pytest.raises(SchemaError):
        _write(over, ">", bytearray())


def test_short_keeps_error_quotes_within_forty_characters() -> None:
    assert short("x" * 38) == repr("x" * 38)  # exactly 40 characters: unchanged
    cut = short("x" * 39)  # 41 characters: cut to 40
    assert len(cut) == 40 and cut.endswith("...")
    assert len(short("x" * 10_000)) == 40


@pytest.mark.parametrize(
    ("schema", "size"),
    [
        (I8, 1),
        (U8, 1),
        (I16, 2),
        (U16, 2),
        (I32, 4),
        (U32, 4),
        (I64, 8),
        (U64, 8),
        (SGL, 4),
        (DBL, 8),
        (EXT, 16),
        (Timestamp, 16),
        (Boolean, 1),
        (Cluster([("a", I16), ("b", Timestamp)]), 18),
        (String(), None),
        (Bytes, None),
        (Array(I8), None),
        (Cluster([("a", I16), ("s", String())]), None),
    ],
)
def test_fixed_sizes_are_pinned(schema: object, size: int | None) -> None:
    assert fixed_size(schema) == size  # type: ignore[arg-type]


def test_arrays_of_16_byte_scalars_unpack_without_sizes() -> None:
    stamps = [LVTimestamp(1, 2), LVTimestamp(-3, 4)]
    raw = pack(Array(Timestamp), stamps, prepend_size=False)
    assert unpack(Array(Timestamp), raw, prepend_size=False) == stamps
    ext_raw = pack(Array(EXT), [1.0, -2.5], prepend_size=False)
    assert unpack(Array(EXT), ext_raw, prepend_size=False) == [1.0, -2.5]


def test_a_short_time_stamp_array_fails_before_reading_elements() -> None:
    with pytest.raises(TruncatedDataError, match="array declares 3 elements of 16 bytes"):
        unpack(Array(Timestamp), bytes.fromhex("00000003") + bytes(16))


def test_any_nonzero_byte_reads_true() -> None:
    assert unpack(Boolean, b"\x00") is False
    assert all(unpack(Boolean, bytes([b])) is True for b in range(1, 256))
    assert unpack(BoolArray, bytes.fromhex("0000000300027f")) == [False, True, True]


def test_negative_lengths_are_data_errors() -> None:
    for schema in (String(), Bytes, Array(I8)):
        with pytest.raises(DataError, match="negative"):
            unpack(schema, bytes.fromhex("ffffffff"))


def test_trailing_count_and_error_hierarchy() -> None:
    with pytest.raises(TrailingDataError) as caught:
        unpack(I16, bytes(5))
    assert caught.value.count == 3
    for cls in (DataError, TruncatedDataError, TrailingDataError, SchemaError):
        assert issubclass(cls, LVFlattenError) and issubclass(cls, ValueError)
    assert issubclass(TruncatedDataError, DataError) and issubclass(TrailingDataError, DataError)
    assert not issubclass(SchemaError, DataError)
