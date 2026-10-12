"""The ``Bytes`` node, bytes-like input, and the ``LVTimestamp`` datetime helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from lvflatten import U8, Array, Bytes, Cluster, LVTimestamp, String, Timestamp, pack, unpack


def test_bytes_round_trip_and_wire_form() -> None:
    assert pack(Bytes, b"\x00\xff") == b"\x00\x00\x00\x02\x00\xff"
    assert unpack(Bytes, b"\x00\x00\x00\x02\x00\xff") == b"\x00\xff"
    assert pack(Bytes, bytearray(b"ab")) == pack(Bytes, memoryview(b"ab"))


def test_bytes_matches_a_u8_array_and_a_string_on_the_wire() -> None:
    assert pack(Bytes, b"\x01\x02\x03") == pack(Array(U8), [1, 2, 3])
    assert pack(Bytes, b"ABC") == pack(String(), "ABC")


def test_bytes_without_size_prefix() -> None:
    assert pack(Bytes, b"\x01\x02", prepend_size=False) == b"\x01\x02"
    assert unpack(Bytes, b"\x01\x02", prepend_size=False) == b"\x01\x02"


def test_bytes_inside_a_cluster() -> None:
    schema = Cluster([("blob", Bytes), ("n", U8)])
    blob = pack(schema, {"blob": b"\xfe", "n": 9})
    assert blob == b"\x00\x00\x00\x01\xfe\x09"
    assert unpack(schema, blob) == {"blob": b"\xfe", "n": 9}


@pytest.mark.parametrize("kind", [bytes, bytearray, memoryview])
def test_unpack_accepts_any_bytes_like(kind: type) -> None:
    assert unpack(String(), kind(b"\x00\x00\x00\x01A")) == "A"
    assert unpack(String(), kind(b"A"), prepend_size=False) == "A"
    assert unpack(Bytes, kind(b"A"), prepend_size=False) == b"A"


def test_unpacked_bytes_are_immutable_bytes() -> None:
    assert type(unpack(Bytes, bytearray(b"\x00\x00\x00\x01A"))) is bytes
    assert type(unpack(Bytes, bytearray(b"A"), prepend_size=False)) is bytes


_UTC = timezone.utc


def test_unix_epoch_converts_exactly() -> None:
    stamp = LVTimestamp.from_datetime(datetime(1970, 1, 1, tzinfo=_UTC))
    assert stamp == LVTimestamp(2082844800, 0)
    assert stamp.to_datetime() == datetime(1970, 1, 1, tzinfo=_UTC)


def test_from_datetime_respects_the_timezone() -> None:
    plus_two = timezone(timedelta(hours=2))
    assert LVTimestamp.from_datetime(datetime(1904, 1, 1, 2, tzinfo=plus_two)) == (0, 0)


def test_naive_datetime_is_refused() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        LVTimestamp.from_datetime(datetime(2000, 1, 1))


def test_microseconds_survive_a_round_trip() -> None:
    for micro in (0, 1, 499_999, 500_000, 999_999):
        moment = datetime(2026, 10, 12, 8, 30, 15, micro, tzinfo=_UTC)
        assert LVTimestamp.from_datetime(moment).to_datetime() == moment


def test_fraction_is_two_to_the_minus_64() -> None:
    assert LVTimestamp(0, 1 << 63).to_datetime() == datetime(1904, 1, 1, 0, 0, 0, 500000, _UTC)


def test_dates_before_1904_are_negative_seconds() -> None:
    stamp = LVTimestamp.from_datetime(datetime(1903, 12, 31, 23, 59, 59, tzinfo=_UTC))
    assert stamp == LVTimestamp(-1, 0)
    assert unpack(Timestamp, pack(Timestamp, stamp)) == stamp


def test_out_of_range_time_stamp_raises_value_error() -> None:
    with pytest.raises(ValueError, match="outside the range"):
        LVTimestamp((1 << 63) - 1, 0).to_datetime()
