"""Contracts added after the fourth blind mutation round.

The little-endian vectors here are hand-derived from the layout GUIDE section 3 documents
(each number byte-swapped on its own; a time stamp as I64 seconds then U64 fraction; an EXT
as its 16 bytes reversed). No LabVIEW capture of little-endian output exists.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone, tzinfo

import pytest
from _cli_command import run_cli

from lvflatten import (
    EXT,
    I8,
    I16,
    I32,
    Array,
    Cluster,
    LVTimestamp,
    SchemaError,
    Timestamp,
    pack,
    unpack,
)
from lvflatten._errors import count_text

_LE_CASES = [
    (Timestamp, LVTimestamp(1, 2), "01000000000000000200000000000000"),
    (EXT, 1.0, "0000000000000000000000000000ff3f"),
    (
        Cluster([("a", I8), ("b", I16), ("c", I32), ("t", Timestamp)]),
        {"a": 1, "b": 2, "c": 3, "t": LVTimestamp(-1, 1 << 63)},
        "01020003000000ffffffffffffffff0000000000000080",
    ),
]


@pytest.mark.parametrize(("schema", "value", "hex_bytes"), _LE_CASES)
def test_little_endian_golden_bytes(schema: object, value: object, hex_bytes: str) -> None:
    assert pack(schema, value, byte_order="little").hex() == hex_bytes  # type: ignore[arg-type]
    assert unpack(schema, bytes.fromhex(hex_bytes), byte_order="little") == value  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("schema_text", "json_text"),
    [("array(timestamp, 2)", "[[[1, 2]], [[3, 4]]]"), ("array(bytes, 2)", '[["ff", ""]]')],
)
def test_cli_round_trips_two_dimensional_arrays_of_pairs_and_bytes(
    schema_text: str, json_text: str
) -> None:
    flat = run_cli("flatten", "-s", schema_text, "-j", json_text)
    assert flat.returncode == 0, flat.stderr
    back = run_cli("unflatten", "-s", schema_text, "-x", flat.stdout.strip())
    assert back.returncode == 0 and json.loads(back.stdout) == json.loads(json_text)


def test_cli_prints_bytes_and_time_stamps_inside_clusters() -> None:
    schema = "cluster(b:bytes, t:timestamp, inner:cluster(c:bytes))"
    hex_input = "00000001ff00000000000000010000000000000002000000020a0b"
    result = run_cli("unflatten", "-s", schema, "-x", hex_input)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"b": "ff", "t": [1, 2], "inner": {"c": "0a0b"}}


def test_count_text_threshold_is_exactly_two_to_the_63() -> None:
    assert count_text(2**62) == "4611686018427387904"
    assert count_text(2**63 - 1) == "9223372036854775807"
    assert count_text(2**63) == "more than 2**63"


def test_array_messages_switch_at_two_to_the_63() -> None:
    def message(last: int) -> str:
        dims = (2**30).to_bytes(4, "big") * 2 + last.to_bytes(4, "big")
        with pytest.raises(ValueError) as caught:
            unpack(Array(I8, 3), dims)
        return str(caught.value)

    assert "declares more than 2**63 elements" in message(8)
    assert "declares 4611686018427387904 elements" in message(4)


def test_an_empty_hex_option_is_empty_input_and_stdin_is_ignored() -> None:
    result = run_cli("unflatten", "-s", "cluster()", "-x", "", stdin="zz junk")
    assert result.returncode == 0 and json.loads(result.stdout) == {}


def test_an_empty_json_option_is_an_error_and_stdin_is_ignored() -> None:
    result = run_cli("flatten", "-s", "i8", "-j", "", stdin="5")
    assert result.returncode == 1 and result.stdout == ""


def test_default_output_is_json_indented_by_two() -> None:
    result = run_cli("unflatten", "-s", "array(i8)", "-x", "0000000101")
    assert result.stdout.rstrip("\n") == json.dumps([1], indent=2)


class _NoOffset(tzinfo):
    def utcoffset(self, dt: datetime | None) -> timedelta | None:
        return None

    def dst(self, dt: datetime | None) -> timedelta | None:
        return None

    def tzname(self, dt: datetime | None) -> str | None:
        return None


def test_from_datetime_refuses_a_tzinfo_without_an_offset() -> None:
    with pytest.raises(SchemaError, match="timezone-aware"):
        LVTimestamp.from_datetime(datetime(2000, 1, 1, tzinfo=_NoOffset()))
    with pytest.raises(SchemaError, match="timezone-aware"):
        LVTimestamp.from_datetime(datetime(2000, 1, 1))


def test_from_datetime_before_1904_with_a_fraction_and_far_dates() -> None:
    half_before = datetime(1903, 12, 31, 23, 59, 59, 500_000, tzinfo=timezone.utc)
    assert LVTimestamp.from_datetime(half_before) == LVTimestamp(-1, 1 << 63)
    far = datetime(9999, 12, 31, 23, 59, 59, 999_999, tzinfo=timezone.utc)
    stamp = LVTimestamp.from_datetime(far)
    assert stamp.seconds == 255_485_145_599
    assert stamp.to_datetime() == far
