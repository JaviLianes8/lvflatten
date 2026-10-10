import pytest

from lvflatten import DBL, I16, I32, Array, SchemaError, String, pack, unpack


def test_one_dimensional_array_round_trips() -> None:
    schema = Array(I32)
    assert unpack(schema, pack(schema, [1, 2, 3])) == [1, 2, 3]


def test_empty_array_round_trips() -> None:
    schema = Array(DBL)
    assert unpack(schema, pack(schema, [])) == []


def test_one_dimensional_array_layout() -> None:
    # I32 count 2, then the two I16 elements.
    assert pack(Array(I16), [7, 8]) == b"\x00\x00\x00\x02\x00\x07\x00\x08"


def test_array_of_strings_round_trips() -> None:
    schema = Array(String())
    assert unpack(schema, pack(schema, ["a", "bb"])) == ["a", "bb"]


def test_two_dimensional_array_round_trips() -> None:
    schema = Array(I32, ndims=2)
    value = [[1, 2, 3], [4, 5, 6]]
    assert unpack(schema, pack(schema, value)) == value


def test_two_dimensional_array_writes_both_dimension_sizes() -> None:
    schema = Array(I16, ndims=2)
    packed = pack(schema, [[1], [2]])
    assert packed[:8] == b"\x00\x00\x00\x02\x00\x00\x00\x01"


def test_array_needs_at_least_one_dimension() -> None:
    with pytest.raises(SchemaError):
        Array(I32, ndims=0)


def test_array_rejects_wrong_nesting() -> None:
    with pytest.raises(SchemaError):
        pack(Array(I32), 5)
