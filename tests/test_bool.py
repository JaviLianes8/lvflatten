import pytest

from lvflatten import BoolArray, Boolean, SchemaError, pack, unpack


def test_boolean_round_trips() -> None:
    assert unpack(Boolean, pack(Boolean, True)) is True
    assert unpack(Boolean, pack(Boolean, False)) is False


def test_boolean_is_one_byte() -> None:
    assert pack(Boolean, True) == b"\x01"
    assert pack(Boolean, False) == b"\x00"


def test_boolean_rejects_non_bool() -> None:
    with pytest.raises(SchemaError):
        pack(Boolean, 1)


def test_boolean_array_round_trips() -> None:
    for value in ([], [True], [True, False, True], [False] * 9 + [True]):
        assert unpack(BoolArray, pack(BoolArray, value)) == value


def test_boolean_array_is_bit_packed_msb_first() -> None:
    # count 3 as I32, then 0b10100000 in the one packed byte.
    assert pack(BoolArray, [True, False, True]) == b"\x00\x00\x00\x03\xa0"


def test_boolean_array_spans_multiple_bytes() -> None:
    value = [True, False, False, False, False, False, False, False, True]
    assert pack(BoolArray, value) == b"\x00\x00\x00\x09\x80\x80"


def test_boolean_array_rejects_non_bool_elements() -> None:
    with pytest.raises(SchemaError):
        pack(BoolArray, [True, 1, False])
