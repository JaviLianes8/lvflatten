"""Boundary contracts added after the blind mutation round of the 1.0 review."""

from __future__ import annotations

import struct
import threading

import pytest

from lvflatten import (
    EXT,
    I8,
    I32,
    Array,
    Cluster,
    DataError,
    LVTimestamp,
    Schema,
    SchemaError,
    String,
    Timestamp,
    TruncatedDataError,
    format_schema,
    pack,
    parse_schema,
    unpack,
)
from lvflatten._cli import main


def test_ext_keeps_the_nan_payload() -> None:
    (nan,) = struct.unpack(">d", bytes.fromhex("7ff8000000000123"))
    assert pack(EXT, nan).hex() == "7fff8000000000123" + "0" * 15
    (negative,) = struct.unpack(">d", bytes.fromhex("fff8000000000001"))
    assert pack(EXT, negative).hex() == "ffff8000000000001" + "0" * 15


def test_time_stamp_seconds_reach_both_i64_limits() -> None:
    lowest = LVTimestamp(-(2**63), 0)
    assert pack(Timestamp, lowest) == b"\x80" + bytes(15)
    assert unpack(Timestamp, b"\x80" + bytes(15)) == lowest
    highest = LVTimestamp(2**63 - 1, 2**64 - 1)
    assert pack(Timestamp, highest) == b"\x7f" + b"\xff" * 15
    with pytest.raises(SchemaError):
        pack(Timestamp, LVTimestamp(-(2**63) - 1, 0))


def test_rows_longer_than_the_first_are_ragged_too() -> None:
    with pytest.raises(SchemaError, match="ragged"):
        pack(Array(I8, 2), [[1, 2], [3, 4, 5]])


def test_dots_dashes_and_underscores_are_bare_names() -> None:
    schema = Cluster([("a.b", I32), ("x-y_1", I32)])
    assert format_schema(schema) == "cluster(a.b:i32, x-y_1:i32)"
    assert parse_schema("cluster(a.b:i32, x-y_1:i32)") == schema


def test_variable_size_clusters_cannot_be_read_without_sizes() -> None:
    mixed = Array(Cluster([("a", I32), ("s", String())]))
    with pytest.raises(SchemaError, match="fixed-size"):
        unpack(mixed, bytes(8), prepend_size=False)
    with pytest.raises(SchemaError, match="fixed-size"):
        unpack(Array(Cluster([])), b"", prepend_size=False)


def test_the_array_size_pre_check_is_exact() -> None:
    with pytest.raises(TruncatedDataError, match="array declares 2 elements of 4 bytes"):
        unpack(Array(I32), b"\x00\x00\x00\x02" + bytes(7))
    assert unpack(Array(I32), b"\x00\x00\x00\x02" + bytes(8)) == [0, 0]


@pytest.mark.parametrize("digit", ["\u0662", "\uff12", "\u00b2"])
def test_dimension_counts_are_ascii_digits_only(digit: str) -> None:
    with pytest.raises(SchemaError):
        parse_schema(f"array(i32, {digit})")


def test_cli_names_a_missing_cluster_field(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["flatten", "-s", "cluster(a:i32, b:i32)", "-j", '{"a": 1}']) == 1
    assert "missing field 'b'" in capsys.readouterr().err


def _finishes(schema: Schema, data: bytes, seconds: float) -> bool:
    outcome: list[BaseException] = []

    def work() -> None:
        try:
            unpack(schema, data)
        except BaseException as exc:  # recorded and checked by the caller
            outcome.append(exc)

    worker = threading.Thread(target=work, daemon=True)
    worker.start()
    worker.join(seconds)
    return not worker.is_alive() and len(outcome) == 1 and isinstance(outcome[0], DataError)


@pytest.mark.parametrize(
    ("schema", "data"),
    [
        (Array(I32, 2), b"\x7f\xff\xff\xff\x00\x00\x00\x00"),
        (Array(Cluster([])), b"\x7f\xff\xff\xff"),
    ],
    ids=["empty_rows", "empty_clusters"],
)
def test_blow_up_is_refused_under_a_hard_deadline(schema: Schema, data: bytes) -> None:
    # A bounded probe first, so a broken budget fails here instead of leaving a thread
    # that builds 2**31 objects behind the rest of the suite.
    probe = (2_000_000).to_bytes(4, "big") + data[4:]
    with pytest.raises(DataError):
        unpack(schema, probe)
    assert _finishes(schema, data, 2.0)
