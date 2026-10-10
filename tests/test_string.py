import pytest

from lvflatten import SchemaError, String, TruncatedDataError, pack, unpack


def test_string_round_trips() -> None:
    schema = String()
    for value in ("", "A", "hello world", "unicode: éè"):
        assert unpack(schema, pack(schema, value)) == value


def test_string_has_an_i32_length_prefix() -> None:
    assert pack(String(), "ABC") == b"\x00\x00\x00\x03ABC"


def test_empty_string_is_just_the_zero_prefix() -> None:
    assert pack(String(), "") == b"\x00\x00\x00\x00"


def test_string_honours_the_encoding() -> None:
    schema = String("latin-1")
    assert pack(schema, "ÿ") == b"\x00\x00\x00\x01\xff"
    assert unpack(schema, b"\x00\x00\x00\x01\xff") == "ÿ"


def test_string_rejects_non_str() -> None:
    with pytest.raises(SchemaError):
        pack(String(), 123)


def test_truncated_string_body_raises() -> None:
    with pytest.raises(TruncatedDataError):
        unpack(String(), b"\x00\x00\x00\x05AB")
