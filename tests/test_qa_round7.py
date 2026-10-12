"""Contracts added after the seventh blind mutation round."""

from __future__ import annotations

import codecs
import json
import struct

import pytest
from _cli_command import run_cli

from lvflatten import (
    I8,
    I32,
    SGL,
    Array,
    Cluster,
    DataError,
    LVTimestamp,
    SchemaError,
    String,
    Timestamp,
    format_schema,
    pack,
    parse_schema,
    unpack,
)


def test_float_range_errors_name_the_node() -> None:
    with pytest.raises(SchemaError, match=r"for a SGL$"):
        pack(SGL, 1e300)


def test_a_time_stamp_packs_from_a_plain_pair() -> None:
    assert pack(Timestamp, (1, 2)) == pack(Timestamp, LVTimestamp(1, 2))
    assert isinstance(unpack(Timestamp, pack(Timestamp, (1, 2))), LVTimestamp)


def test_rows_of_empty_cluster_arrays_are_charged_to_the_budget() -> None:
    with pytest.raises(DataError):
        unpack(Array(Cluster([]), 2), struct.pack(">ii", 600, 1))
    assert unpack(Array(Cluster([]), 2), struct.pack(">ii", 1, 1)) == [[{}]]


def test_cluster_equality_follows_field_order() -> None:
    assert Cluster([("a", I32), ("b", I8)]) != Cluster([("b", I8), ("a", I32)])
    assert Cluster([("a", I32), ("b", I8)]) == Cluster({"a": I32, "b": I8})


def _my_codec(name: str) -> codecs.CodecInfo | None:
    if name.replace("_", " ") != "lvflatten test codec":
        return None
    utf8 = codecs.lookup("utf-8")
    return codecs.CodecInfo(utf8.encode, utf8.decode, name="lvflatten test codec")


def test_quoted_encoding_names_parse_and_round_trip() -> None:
    assert parse_schema('string("cp1252")') == String("cp1252")
    codecs.register(_my_codec)
    try:
        node = String("lvflatten test codec")
        assert parse_schema(format_schema(node)) == node
    finally:
        codecs.unregister(_my_codec)


def test_cli_output_is_ascii_json() -> None:
    result = run_cli("unflatten", "-s", "string", "-x", "00000002c481")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().isascii()
    assert json.loads(result.stdout) == "ā"


def test_cli_without_a_command_is_a_usage_error() -> None:
    result = run_cli()
    assert result.returncode == 2
    assert "required" in result.stderr and "Traceback" not in result.stderr


def test_cli_refuses_a_string_where_an_array_is_expected() -> None:
    result = run_cli("flatten", "-s", "array(string)", "-j", '"ab"')
    assert result.returncode == 1
    assert "an array value must be a JSON array" in result.stderr
