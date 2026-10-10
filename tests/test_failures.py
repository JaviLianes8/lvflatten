import pytest

from lvflatten import (
    DBL,
    I32,
    Array,
    Boolean,
    Cluster,
    LVFlattenError,
    String,
    TruncatedDataError,
    pack,
    unpack,
)


def test_truncated_scalar_raises() -> None:
    with pytest.raises(TruncatedDataError):
        unpack(I32, b"\x00\x00")


def test_truncated_double_raises() -> None:
    with pytest.raises(TruncatedDataError):
        unpack(DBL, b"\x00\x00\x00\x00")


def test_trailing_bytes_after_a_value_raise() -> None:
    with pytest.raises(LVFlattenError):
        unpack(I32, b"\x00\x00\x00\x01\x99")


def test_trailing_bytes_after_a_cluster_raise() -> None:
    schema = Cluster([("a", I32), ("ok", Boolean)])
    good = pack(schema, {"a": 1, "ok": True})
    with pytest.raises(LVFlattenError):
        unpack(schema, good + b"\x00")


def test_truncated_array_elements_raise() -> None:
    # Claims three I32 elements but supplies only two.
    data = b"\x00\x00\x00\x03\x00\x00\x00\x01\x00\x00\x00\x02"
    with pytest.raises(TruncatedDataError):
        unpack(Array(I32), data)


def test_schema_error_is_an_lvflatten_error() -> None:
    assert issubclass(TruncatedDataError, LVFlattenError)


def test_wrong_string_length_prefix_is_caught() -> None:
    with pytest.raises(TruncatedDataError):
        unpack(String(), b"\x00\x00\x00\x10short")
