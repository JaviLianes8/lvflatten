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


def test_boolean_array_is_one_byte_per_element() -> None:
    # count 3 as I32, then one byte per element (0x01, 0x00, 0x01), as LabVIEW flattens it.
    assert pack(BoolArray, [True, False, True]) == b"\x00\x00\x00\x03\x01\x00\x01"


def test_boolean_array_byte_length_tracks_count() -> None:
    value = [True, False, False, False, False, False, False, False, True]
    assert pack(BoolArray, value) == b"\x00\x00\x00\x09\x01\x00\x00\x00\x00\x00\x00\x00\x01"


def test_boolean_array_rejects_non_bool_elements() -> None:
    with pytest.raises(SchemaError):
        pack(BoolArray, [True, 1, False])
