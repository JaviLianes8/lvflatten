"""EXT: IEEE 754 binary128 in 16 bytes, checked against an independent exact-rational oracle.

The layout was settled by real LabVIEW 2026 output (see ``test_real_labview.py``); here the
codec is also compared with a second, deliberately different implementation that builds the
binary128 bits from ``fractions.Fraction`` arithmetic rather than ``math.frexp``.
"""

from __future__ import annotations

import math
import random
import struct
from fractions import Fraction

import pytest

from lvflatten import EXT, SchemaError, pack, unpack


def _oracle(value: float) -> bytes:
    """binary128 bits of a finite nonzero double, by exact rational arithmetic."""
    sign = 1 if value < 0 else 0
    exact = abs(Fraction(value))
    exponent = exact.numerator.bit_length() - exact.denominator.bit_length()
    if Fraction(2) ** exponent > exact:
        exponent -= 1
    fraction = exact / Fraction(2) ** exponent - 1  # in [0, 1)
    bits = fraction * (1 << 112)
    assert bits.denominator == 1
    word = (sign << 127) | ((exponent + 16383) << 112) | int(bits)
    return word.to_bytes(16, "big")


@pytest.mark.parametrize(
    "value",
    [0.0, 1.0, -1.0, 2.5, -0.1, 1234.5678, 1e100, 1e-100, math.pi, 5e-324, 1.7976931348623157e308],
)
def test_extended_round_trips_double_values(value: float) -> None:
    assert unpack(EXT, pack(EXT, value)) == value


def test_extended_is_sixteen_bytes() -> None:
    assert len(pack(EXT, 1.0)) == 16


def test_extended_one_has_no_explicit_integer_bit() -> None:
    assert pack(EXT, 1.0) == bytes.fromhex("3fff") + b"\x00" * 14
    assert pack(EXT, -2.5) == bytes.fromhex("c0004000") + b"\x00" * 12


def test_codec_matches_the_rational_oracle_on_random_doubles() -> None:
    rng = random.Random(128)
    for _ in range(2000):
        (value,) = struct.unpack(">d", rng.randbytes(8))
        if math.isnan(value) or math.isinf(value) or value == 0.0:
            continue
        assert pack(EXT, value) == _oracle(value)
        assert unpack(EXT, _oracle(value)) == value


def test_little_endian_reverses_all_sixteen_bytes() -> None:
    assert pack(EXT, 0.1, byte_order="little") == pack(EXT, 0.1)[::-1]
    assert unpack(EXT, pack(EXT, 0.1)[::-1], byte_order="little") == 0.1


def test_decoding_rounds_to_the_nearest_double() -> None:
    one_plus_tiny = bytes.fromhex("3fff") + b"\x00" * 13 + b"\x01"
    assert unpack(EXT, one_plus_tiny) == 1.0
    halfway_up = bytes.fromhex("3fff0000000000001800") + b"\x00" * 6  # 1 + 1.5 ulp
    assert unpack(EXT, halfway_up) == 1.0 + 2 * 2**-52


def test_out_of_double_range_decodes_to_infinity_or_zero() -> None:
    assert unpack(EXT, bytes.fromhex("7ffe") + b"\x00" * 14) == math.inf
    assert unpack(EXT, bytes.fromhex("fffe") + b"\x00" * 14) == -math.inf
    assert unpack(EXT, bytes.fromhex("0001") + b"\x00" * 14) == 0.0
    assert unpack(EXT, b"\x00" * 15 + b"\x01") == 0.0  # a binary128 subnormal


def test_extended_keeps_signed_zero() -> None:
    result = unpack(EXT, pack(EXT, -0.0))
    assert isinstance(result, float)
    assert math.copysign(1.0, result) == -1.0


def test_extended_round_trips_infinities() -> None:
    assert pack(EXT, math.inf) == bytes.fromhex("7fff") + b"\x00" * 14
    assert unpack(EXT, pack(EXT, -math.inf)) == -math.inf


def test_nan_keeps_its_sign_and_quiet_bit() -> None:
    assert pack(EXT, math.nan) == bytes.fromhex("7fff8000") + b"\x00" * 12
    negative = math.copysign(math.nan, -1.0)
    decoded = unpack(EXT, pack(EXT, negative))
    assert isinstance(decoded, float) and math.isnan(decoded)
    assert math.copysign(1.0, decoded) == math.copysign(1.0, negative)


def test_extended_rejects_non_number() -> None:
    with pytest.raises(SchemaError):
        pack(EXT, None)
