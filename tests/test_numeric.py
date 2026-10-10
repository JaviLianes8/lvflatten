import pytest

from lvflatten import (
    DBL,
    I8,
    I16,
    I32,
    I64,
    SGL,
    U8,
    U16,
    U32,
    U64,
    SchemaError,
    pack,
    unpack,
)

INTEGER_TYPES = [I8, I16, I32, I64, U8, U16, U32, U64]


@pytest.mark.parametrize("schema", INTEGER_TYPES)
@pytest.mark.parametrize("value", [0, 1, 100])
def test_integers_round_trip(schema: object, value: int) -> None:
    assert unpack(schema, pack(schema, value)) == value  # type: ignore[arg-type]


def test_signed_integers_round_trip_negatives() -> None:
    for schema in (I8, I16, I32, I64):
        assert unpack(schema, pack(schema, -5)) == -5


def test_integer_width_is_fixed() -> None:
    assert len(pack(I8, 1)) == 1
    assert len(pack(I16, 1)) == 2
    assert len(pack(I32, 1)) == 4
    assert len(pack(I64, 1)) == 8


def test_unsigned_full_range_round_trips() -> None:
    assert unpack(U8, pack(U8, 255)) == 255
    assert unpack(U16, pack(U16, 65535)) == 65535
    assert unpack(U32, pack(U32, 4294967295)) == 4294967295


def test_integer_out_of_range_raises() -> None:
    with pytest.raises(SchemaError):
        pack(U8, 256)
    with pytest.raises(SchemaError):
        pack(I8, 200)


def test_integer_rejects_bool() -> None:
    with pytest.raises(SchemaError):
        pack(I32, True)


def test_double_round_trips() -> None:
    for value in (0.0, 1.0, -2.5, 3.141592653589793, 1e300):
        assert unpack(DBL, pack(DBL, value)) == value


def test_single_round_trips_exact_values() -> None:
    for value in (0.0, 1.5, -2.25, 256.0):
        assert unpack(SGL, pack(SGL, value)) == value


def test_float_accepts_int() -> None:
    assert unpack(DBL, pack(DBL, 7)) == 7.0


def test_float_rejects_non_number() -> None:
    with pytest.raises(SchemaError):
        pack(DBL, "x")
