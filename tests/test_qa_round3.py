"""Contracts added after the third blind mutation round: CLI byte order, reprs, hints."""

from __future__ import annotations

import sys
import typing

import pytest
from _cli_command import run_cli

import lvflatten
from lvflatten import DBL, I16, String, pack


@pytest.mark.parametrize(
    ("schema_text", "json_text", "schema", "value"),
    [("i16", "1", I16, 1), ("dbl", "1.0", DBL, 1.0)],
)
def test_cli_flatten_little_matches_pack_little(
    schema_text: str, json_text: str, schema: object, value: object
) -> None:
    flat = run_cli("flatten", "-s", schema_text, "-j", json_text, "--little")
    assert flat.returncode == 0, flat.stderr
    assert flat.stdout.strip() == pack(schema, value, byte_order="little").hex()  # type: ignore[arg-type]
    back = run_cli("unflatten", "-s", schema_text, "-x", flat.stdout.strip(), "--little")
    assert back.returncode == 0 and float(back.stdout) == value


def test_cli_flatten_little_writes_little_endian_bytes() -> None:
    assert run_cli("flatten", "-s", "i16", "-j", "1", "--little").stdout.strip() == "0100"


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16", "utf-16-le", "cp1252"])
def test_string_repr_round_trips(encoding: str) -> None:
    node = String(encoding)
    assert eval(repr(node), {"String": String}) == node


def test_only_utf_8_strings_repr_without_an_argument() -> None:
    assert repr(String("UTF8")) == "String()"
    assert repr(String("utf-16")) == "String('utf-16')"


def test_cli_rejects_non_ascii_bytes_with_the_hex_message() -> None:
    result = run_cli("flatten", "-s", "bytes", "-j", '"\u00e9\u00e9"')
    assert result.returncode == 1
    assert "bytes must be given as a hex string" in result.stderr


def test_buffer_hint_is_the_abc_from_python_3_12() -> None:
    for function in (lvflatten.unpack, lvflatten.unpack_from):
        hint = typing.get_type_hints(function)["data"]
        if sys.version_info >= (3, 12):
            import collections.abc

            assert hint is collections.abc.Buffer
        else:
            assert hint == bytes | bytearray | memoryview
