import pytest

from lvflatten import DBL, I32, U16, Array, SchemaError, String, pack, unpack


def test_little_endian_reverses_integer_bytes() -> None:
    assert pack(U16, 0x1234, byte_order="little") == b"\x34\x12"
    assert unpack(U16, b"\x34\x12", byte_order="little") == 0x1234


def test_little_endian_round_trips_a_cluster_like_array() -> None:
    schema = Array(I32)
    packed = pack(schema, [1, 2, 3], byte_order="little")
    assert unpack(schema, packed, byte_order="little") == [1, 2, 3]


def test_unknown_byte_order_raises() -> None:
    with pytest.raises(SchemaError):
        pack(I32, 1, byte_order="middle")


def test_prepend_size_false_drops_top_level_string_prefix() -> None:
    assert pack(String(), "ABC", prepend_size=False) == b"ABC"
    assert unpack(String(), b"ABC", prepend_size=False) == "ABC"


def test_prepend_size_false_drops_top_level_array_prefix() -> None:
    packed = pack(Array(I32), [1, 2], prepend_size=False)
    assert packed == b"\x00\x00\x00\x01\x00\x00\x00\x02"
    assert unpack(Array(I32), packed, prepend_size=False) == [1, 2]


def test_prepend_size_false_still_keeps_nested_prefixes() -> None:
    # The outer array loses its count; the inner strings keep theirs.
    packed = pack(Array(String()), ["a"], prepend_size=False)
    assert packed == b"\x00\x00\x00\x01a"


def test_prepend_size_false_needs_a_one_dimensional_array() -> None:
    with pytest.raises(SchemaError):
        unpack(Array(I32, ndims=2), b"", prepend_size=False)


def test_prepend_size_false_needs_fixed_size_elements() -> None:
    with pytest.raises(SchemaError):
        unpack(Array(String()), b"abc", prepend_size=False)


def test_prepend_size_false_rejects_partial_element() -> None:
    with pytest.raises(SchemaError):
        unpack(Array(DBL), b"\x00\x00\x00", prepend_size=False)
