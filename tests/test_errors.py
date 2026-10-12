"""The error contract: which class is raised for what, and that messages stay short."""

from __future__ import annotations

import math
from collections.abc import Callable

import pytest

from lvflatten import (
    DBL,
    EXT,
    I8,
    I32,
    SGL,
    U64,
    Array,
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


def test_hierarchy() -> None:
    assert issubclass(SchemaError, LVFlattenError) and issubclass(SchemaError, ValueError)
    assert issubclass(DataError, LVFlattenError) and issubclass(DataError, ValueError)
    assert issubclass(TruncatedDataError, DataError)
    assert issubclass(TrailingDataError, DataError)
    assert not issubclass(SchemaError, DataError)


def test_trailing_bytes_raise_trailing_data_error_with_count() -> None:
    with pytest.raises(TrailingDataError) as info:
        unpack(I32, b"\x00\x00\x00\x01\x99\x98")
    assert info.value.count == 2
    assert "2 trailing bytes" in str(info.value)


@pytest.mark.parametrize(
    ("schema", "data"),
    [
        (String(), b"\xff\xff\xff\xfe"),
        (Bytes, b"\x80\x00\x00\x00"),
        (Array(I32), b"\xff\xff\xff\xff"),
        (String(), b"\x00\x00\x00\x01\xff"),
        (String("ascii"), b"\x00\x00\x00\x01\x80"),
    ],
    ids=["neg_string", "neg_bytes", "neg_dim", "bad_utf8", "bad_ascii"],
)
def test_malformed_data_raises_data_error(schema: object, data: bytes) -> None:
    with pytest.raises(DataError):
        unpack(schema, data)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("schema", "value"),
    [
        (I8, 128),
        (I8, 1.0),
        (I8, True),
        (U64, -1),
        (U64, 1 << 64),
        (DBL, 10**400),
        (DBL, "1.0"),
        (SGL, 1e300),
        (EXT, 10**400),
        (Boolean, 1),
        (String(), b"bytes"),
        (String("ascii"), "é"),
        (Bytes, "text"),
        (Timestamp, (1 << 63, 0)),
        (Timestamp, (0, -1)),
        (Timestamp, (0, 1 << 64)),
        (Timestamp, (True, 0)),
        (Timestamp, (1.0, 0)),
        (Timestamp, (1, 2, 3)),
        (Array(I32), 5),
        (Array(I32, 2), [[1, 2], [3]]),
        (Array(I32, 2), [1, 2]),
        (Cluster([("a", I32)]), {"b": 1}),
        (Cluster([("a", I32)]), [1]),
    ],
)
def test_wrong_values_raise_schema_error(schema: object, value: object) -> None:
    with pytest.raises(SchemaError):
        pack(schema, value)  # type: ignore[arg-type]


def test_truncation_reports_offset_and_need() -> None:
    with pytest.raises(TruncatedDataError, match="need 8 bytes at offset 4, only 3 available"):
        unpack(Cluster([("a", I32), ("b", DBL)]), b"\x00" * 7)


def test_array_with_impossible_size_fails_fast() -> None:
    with pytest.raises(TruncatedDataError, match="2147483647 elements"):
        unpack(Array(DBL), b"\x7f\xff\xff\xff")


@pytest.mark.parametrize("order", ["middle", "BIG", "", 1, None])
def test_bad_byte_order_is_a_schema_error(order: object) -> None:
    with pytest.raises(SchemaError):
        pack(I32, 1, byte_order=order)  # type: ignore[arg-type]
    with pytest.raises(SchemaError):
        unpack(I32, b"\x00" * 4, byte_order=order)  # type: ignore[arg-type]


@pytest.mark.parametrize("data", ["00000001", 1, None, [0, 0, 0, 1]])
def test_non_bytes_data_is_a_type_error(data: object) -> None:
    with pytest.raises(TypeError):
        unpack(I32, data)  # type: ignore[arg-type]


def test_messages_never_echo_huge_input() -> None:
    huge = "x" * 100_000
    actions: list[Callable[[], object]] = [
        lambda: pack(I32, 1, byte_order=huge),  # type: ignore[arg-type]
        lambda: String(huge),
        lambda: pack(Cluster([(huge, I32)]), {}),
        lambda: pack(String("ascii"), huge + "é"),
        lambda: unpack(String(), b"\x00\x01\x86\xa0" + b"\xff" * 100_000),
    ]
    for action in actions:
        with pytest.raises(LVFlattenError) as info:
            action()
        assert len(str(info.value)) < 120


def test_values_are_never_echoed_in_messages() -> None:
    with pytest.raises(SchemaError) as info:
        pack(String("ascii"), "secret-token-é")
    assert "secret" not in str(info.value)


def test_nan_and_infinities_are_not_errors() -> None:
    for number in (math.nan, math.inf, -math.inf):
        assert pack(DBL, number)
        assert pack(SGL, number)
        assert pack(EXT, number)
    assert unpack(Timestamp, pack(Timestamp, LVTimestamp(-1, 0))) == LVTimestamp(-1, 0)
