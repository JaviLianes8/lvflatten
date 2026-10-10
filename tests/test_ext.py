import math

import pytest

from lvflatten import EXT, SchemaError, pack, unpack


@pytest.mark.parametrize(
    "value",
    [0.0, 1.0, -1.0, 2.5, -0.1, 1234.5678, 1e100, 1e-100, math.pi],
)
def test_extended_round_trips_double_values(value: float) -> None:
    assert unpack(EXT, pack(EXT, value)) == value


def test_extended_is_sixteen_bytes() -> None:
    assert len(pack(EXT, 1.0)) == 16


def test_extended_one_matches_the_eighty_bit_layout() -> None:
    # 1.0 in 80-bit extended: sign 0, exponent 0x3FFF, significand 0x8000...0, zero padded.
    assert pack(EXT, 1.0) == bytes.fromhex("3fff8000000000000000") + b"\x00" * 6


def test_extended_keeps_signed_zero() -> None:
    result = unpack(EXT, pack(EXT, -0.0))
    assert isinstance(result, float)
    assert math.copysign(1.0, result) == -1.0


def test_extended_round_trips_infinities() -> None:
    assert unpack(EXT, pack(EXT, math.inf)) == math.inf
    assert unpack(EXT, pack(EXT, -math.inf)) == -math.inf


def test_extended_round_trips_nan() -> None:
    assert math.isnan(unpack(EXT, pack(EXT, math.nan)))  # type: ignore[arg-type]


def test_extended_rejects_non_number() -> None:
    with pytest.raises(SchemaError):
        pack(EXT, None)
