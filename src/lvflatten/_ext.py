"""Pack and unpack the LabVIEW extended-precision float.

LabVIEW flattens an extended number as the 80-bit format (one sign bit, a 15-bit exponent
biased by 16383, and a 64-bit significand whose top bit is the explicit integer bit) held
big-endian in the leading ten bytes of a sixteen-byte field, the last six bytes being zero.
The maths here is pure Python so no numpy longdouble (platform-dependent) is involved. Any
value that fits a Python float round-trips exactly; magnitudes beyond the double range are
documented as lossy.
"""

from __future__ import annotations

import math

from ._errors import SchemaError
from ._reader import Reader

_BIAS = 16383
_EXP_ALL_ONES = 0x7FFF
_INTEGER_BIT = 1 << 63
_SIGNIFICAND_MASK = (1 << 64) - 1
_FRACTION_MASK = (1 << 63) - 1
_QUIET_NAN = 0xC000000000000000


def _encode(value: float) -> int:
    """Return the 80 meaningful bits (sign, exponent, significand) packed into an int."""
    if math.isnan(value):
        return (_EXP_ALL_ONES << 64) | _QUIET_NAN
    if math.isinf(value):
        sign = 1 if value < 0 else 0
        return (sign << 79) | (_EXP_ALL_ONES << 64) | _INTEGER_BIT
    sign = 1 if math.copysign(1.0, value) < 0 else 0
    if value == 0.0:
        return sign << 79
    mantissa, exponent = math.frexp(abs(value))  # abs = mantissa * 2**exponent, 0.5 <= m < 1
    significand = int(mantissa * (1 << 64))
    biased = (exponent - 1 + _BIAS) & _EXP_ALL_ONES
    return (sign << 79) | (biased << 64) | (significand & _SIGNIFICAND_MASK)


def _decode(bits: int) -> float:
    sign = (bits >> 79) & 1
    exponent = (bits >> 64) & _EXP_ALL_ONES
    significand = bits & _SIGNIFICAND_MASK
    if exponent == _EXP_ALL_ONES:
        if significand & _FRACTION_MASK:
            return math.nan
        return -math.inf if sign else math.inf
    if exponent == 0 and significand == 0:
        return -0.0 if sign else 0.0
    value = math.ldexp(significand, exponent - _BIAS - 63)
    return -value if sign else value


def pack_ext(value: object, bo: str, out: bytearray) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SchemaError("expected a real number for an extended float")
    packed = _encode(float(value)) << 48
    out += packed.to_bytes(16, "big" if bo == ">" else "little")


def unpack_ext(reader: Reader, bo: str) -> float:
    packed = int.from_bytes(reader.take(16), "big" if bo == ">" else "little")
    return _decode(packed >> 48)
