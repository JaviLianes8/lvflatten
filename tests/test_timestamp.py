import pytest

from lvflatten import LVTimestamp, SchemaError, Timestamp, pack, unpack

# 2082844800 seconds separate the LabVIEW 1904 epoch from the Unix 1970 epoch (NI docs).
UNIX_EPOCH_IN_1904_SECONDS = 2082844800


def test_timestamp_round_trips() -> None:
    value = LVTimestamp(UNIX_EPOCH_IN_1904_SECONDS, 1 << 63)
    assert unpack(Timestamp, pack(Timestamp, value)) == value


def test_timestamp_epoch_is_all_zero() -> None:
    assert pack(Timestamp, LVTimestamp(0, 0)) == b"\x00" * 16


def test_timestamp_is_sixteen_bytes() -> None:
    assert len(pack(Timestamp, LVTimestamp(123, 456))) == 16


def test_timestamp_unix_epoch_vector() -> None:
    packed = pack(Timestamp, LVTimestamp(UNIX_EPOCH_IN_1904_SECONDS, 0))
    assert packed == b"\x00\x00\x00\x00\x7c\x25\xb0\x80" + b"\x00" * 8


def test_timestamp_round_trips_negative_seconds() -> None:
    value = LVTimestamp(-1000, 0)
    assert unpack(Timestamp, pack(Timestamp, value)) == value


def test_timestamp_returns_a_named_tuple() -> None:
    result = unpack(Timestamp, pack(Timestamp, LVTimestamp(5, 6)))
    assert isinstance(result, LVTimestamp)
    assert result.seconds == 5
    assert result.fraction == 6


def test_timestamp_rejects_out_of_range_fraction() -> None:
    with pytest.raises(SchemaError):
        pack(Timestamp, LVTimestamp(0, 1 << 64))
