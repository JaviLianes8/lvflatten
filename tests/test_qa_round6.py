"""Contracts added after the sixth blind mutation round."""

from __future__ import annotations

import pytest
from _cli_command import run_cli

from lvflatten import EXT, I8, U8, SchemaError, String, pack, parse_schema, unpack, unpack_from
from lvflatten._schema import IntType


def test_range_errors_name_the_signedness() -> None:
    with pytest.raises(SchemaError, match="8-bit unsigned integer"):
        pack(U8, 300)
    with pytest.raises(SchemaError, match="8-bit signed integer"):
        pack(I8, 300)


def test_ext_refuses_a_bool() -> None:
    with pytest.raises(SchemaError):
        pack(EXT, True)


def test_a_string_without_size_decodes_with_its_own_encoding() -> None:
    assert unpack(String("cp1252"), b"\xe9", prepend_size=False) == "\u00e9"


def test_integer_nodes_exist_only_for_labview_widths() -> None:
    for bits in (12, 0, 128):
        with pytest.raises(SchemaError, match="unsupported integer width"):
            IntType(bits, True)


@pytest.mark.parametrize("encoding", [5, None, b"utf-8"])
def test_a_string_encoding_must_be_a_name(encoding: object) -> None:
    with pytest.raises(SchemaError, match="must be a codec name"):
        String(encoding)  # type: ignore[arg-type]


def test_an_unterminated_quoted_name_is_refused() -> None:
    with pytest.raises(SchemaError, match="unterminated"):
        parse_schema('cluster("abc:i32)')


@pytest.mark.parametrize("text", [b"i32", None, 5])
def test_schema_text_must_be_a_str(text: object) -> None:
    with pytest.raises(SchemaError, match="must be a str"):
        parse_schema(text)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("schema", "json_text", "message"),
    [
        ("bytes", "5", "bytes must be given as a hex string"),
        ("cluster(a:i8)", "[1]", "a cluster value must be a JSON object"),
    ],
)
def test_cli_reports_wrong_json_shapes(schema: str, json_text: str, message: str) -> None:
    result = run_cli("flatten", "-s", schema, "-j", json_text)
    assert result.returncode == 1
    assert message in result.stderr and "Traceback" not in result.stderr


def test_a_bad_offset_is_quoted_briefly() -> None:
    with pytest.raises(SchemaError) as caught:
        unpack_from(I8, b"\x00", "x" * 10_000)  # type: ignore[arg-type]
    assert len(str(caught.value)) < 120
