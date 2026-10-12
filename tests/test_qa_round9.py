"""Contracts added after the ninth blind mutation round."""

from __future__ import annotations

import array
import codecs
from datetime import timezone

import pytest
from _cli_command import run_cli

from lvflatten import (
    EXT,
    I32,
    Boolean,
    Bytes,
    LVTimestamp,
    SchemaError,
    String,
    Timestamp,
    format_schema,
    pack,
    parse_schema,
)


def test_bytes_from_a_view_of_wide_items_counts_bytes() -> None:
    view = memoryview(array.array("H", [1, 2]))
    assert pack(Bytes, view) == len(bytes(view)).to_bytes(4, "big") + bytes(view)


@pytest.mark.parametrize(
    "action",
    [
        lambda: pack(I32, "x" * 10_000),
        lambda: parse_schema('"' + "x" * 10_000 + '"'),
    ],
    ids=["scalar_type_error", "unexpected_token"],
)
def test_huge_bad_input_is_never_echoed(action: object) -> None:
    with pytest.raises(SchemaError) as caught:
        action()  # type: ignore[operator]
    assert len(str(caught.value)) < 120


def test_syntax_errors_name_the_expected_token() -> None:
    with pytest.raises(SchemaError, match=r"expected '\)'"):
        parse_schema("array(i32:)")


@pytest.mark.parametrize("thing", [5, None, type(I32)])
def test_format_schema_refuses_what_is_not_a_node(thing: object) -> None:
    with pytest.raises(SchemaError):
        format_schema(thing)  # type: ignore[arg-type]


@pytest.mark.parametrize("node", [EXT, Boolean, Timestamp, Bytes, I32])
def test_shared_scalar_nodes_take_no_new_attributes(node: object) -> None:
    with pytest.raises(AttributeError):
        node.extra = 1  # type: ignore[attr-defined]


def test_cli_json_bytes_may_split_a_byte_with_whitespace() -> None:
    result = run_cli("flatten", "-s", "bytes", "-j", '"0 0ff"')
    assert result.returncode == 0 and result.stdout.strip() == "0000000200ff"


def test_cli_help_keeps_one_example_per_line() -> None:
    result = run_cli("--help")
    assert result.returncode == 0
    assert "\n  lvflatten unflatten -s i32 -x 0000002a\n" in result.stdout


def test_cli_output_ends_with_one_newline() -> None:
    assert run_cli("flatten", "-s", "i8", "-j", "5").stdout == "05\n"
    assert run_cli("unflatten", "-s", "i8", "-x", "05").stdout == "5\n"


def test_to_datetime_is_in_utc() -> None:
    moment = LVTimestamp(0, 0).to_datetime()
    assert moment.tzinfo is timezone.utc and moment.tzname() == "UTC"


def _never(data: object, errors: str = "strict", /) -> tuple[str, int]:
    raise UnicodeError("this decoder always fails")


def _encode_only(name: str) -> codecs.CodecInfo | None:
    if name.replace("_", " ") != "lvflatten encode only":
        return None
    return codecs.CodecInfo(codecs.lookup("utf-8").encode, _never, name="lvflatten encode only")


def test_a_codec_whose_decoder_always_fails_is_refused_when_built() -> None:
    codecs.register(_encode_only)
    try:
        with pytest.raises(SchemaError, match="unknown text encoding"):
            String("lvflatten encode only")
    finally:
        codecs.unregister(_encode_only)
