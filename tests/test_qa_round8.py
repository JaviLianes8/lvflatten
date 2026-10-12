"""Contracts added after the eighth blind mutation round."""

from __future__ import annotations

import codecs
import struct

import pytest
from _cli_command import run_cli

from lvflatten import (
    I8,
    Array,
    Cluster,
    DataError,
    SchemaError,
    String,
    Timestamp,
    pack,
    parse_schema,
    unpack,
)


@pytest.mark.parametrize("pair", [(1, True), (1, 1.5), (True, 1), (1.5, 1)])
def test_both_time_stamp_parts_must_be_integers(pair: tuple[object, object]) -> None:
    with pytest.raises(SchemaError, match="must be integers"):
        pack(Timestamp, pair)


def _decode(data: object, errors: str = "strict", /) -> tuple[str, int]:
    if len(memoryview(data)):  # type: ignore[arg-type]
        raise UnicodeError("this codec refuses every byte")
    return "", 0


def _plain_unicode_error_codec(name: str) -> codecs.CodecInfo | None:
    if name.replace("_", " ") != "lvflatten refusing codec":
        return None
    utf8 = codecs.lookup("utf-8")
    return codecs.CodecInfo(utf8.encode, _decode, name="lvflatten refusing codec")


def test_any_unicode_error_while_decoding_is_a_data_error() -> None:
    codecs.register(_plain_unicode_error_codec)
    try:
        with pytest.raises(DataError):
            unpack(String("lvflatten refusing codec"), bytes.fromhex("0000000141"))
    finally:
        codecs.unregister(_plain_unicode_error_codec)


def test_arrays_pack_from_tuples() -> None:
    assert pack(Array(I8), (1, 2)) == pack(Array(I8), [1, 2]) == bytes.fromhex("000000020102")
    assert pack(Array(I8, 2), ((1, 2), (3, 4))) == pack(Array(I8, 2), [[1, 2], [3, 4]])


def test_a_codec_that_fails_on_empty_input_is_refused_when_built() -> None:
    with pytest.raises(SchemaError, match="unknown text encoding"):
        String("undefined")


def test_the_free_budget_is_shared_by_the_whole_value() -> None:
    empties = Array(Cluster([]))
    two = Cluster([("a", empties), ("b", empties)])
    with pytest.raises(DataError):
        unpack(two, struct.pack(">ii", 600, 600))
    assert len(unpack(two, struct.pack(">ii", 300, 300))["b"]) == 300  # type: ignore[index]


def test_schema_text_may_use_any_whitespace() -> None:
    assert parse_schema("cluster(a:i32,\n\tb:i8)") == parse_schema("cluster(a:i32, b:i8)")


def test_cli_hex_may_split_a_byte_with_whitespace() -> None:
    result = run_cli("unflatten", "-s", "i32", "-x", "000 0002a")
    assert result.returncode == 0 and result.stdout.strip() == "42"
