"""Pack and unpack the LabVIEW extended-precision float.

LabVIEW flattens an extended number as 16 bytes in the IEEE 754 binary128 layout: one sign
bit, a 15-bit exponent biased by 16383, and a 112-bit fraction with an implicit leading one.
Real LabVIEW 2026 output confirms it: 1.0 is ``3fff`` followed by fourteen zero bytes, and
0.1 carries the double's fraction moved to the top of the 112 bits.

Encoding a Python ``float`` is exact (a double fits binary128 with room to spare, and its
NaN payload and sign are kept). Decoding rounds the 113-bit significand to the nearest
double; magnitudes beyond the double range become infinity and tiny ones round towards zero.
The maths is pure Python, so no platform ``long double`` is involved.
"""

from __future__ import annotations

import math
import struct

from ._errors import SchemaError
from ._reader import Reader

_BIAS = 16383
_EXP_ALL_ONES = 0x7FFF
_FRACTION_BITS = 112
_HIDDEN = 1 << _FRACTION_BITS
_FRACTION_MASK = _HIDDEN - 1
_DOUBLE_FRACTION_SHIFT = _FRACTION_BITS - 52


def _encode(value: float) -> int:
    """Return the 128 bits (sign, exponent, fraction) of ``value`` as an int."""
    sign = 1 if math.copysign(1.0, value) < 0 else 0
    if math.isnan(value):
        bits = int.from_bytes(struct.pack(">d", value), "big")
        payload = (bits & ((1 << 52) - 1)) << _DOUBLE_FRACTION_SHIFT
        return (sign << 127) | (_EXP_ALL_ONES << _FRACTION_BITS) | payload
    if math.isinf(value):
        return (sign << 127) | (_EXP_ALL_ONES << _FRACTION_BITS)
    if value == 0.0:
        return sign << 127
    mantissa, exponent = math.frexp(abs(value))  # abs = mantissa * 2**exponent, 0.5 <= m < 1
    fraction = int(mantissa * (1 << (_FRACTION_BITS + 1))) - _HIDDEN  # exact: m has <= 53 bits
    biased = exponent - 1 + _BIAS
    return (sign << 127) | (biased << _FRACTION_BITS) | fraction


def _decode(bits: int) -> float:
    sign = -1.0 if bits >> 127 else 1.0
    exponent = (bits >> _FRACTION_BITS) & _EXP_ALL_ONES
    fraction = bits & _FRACTION_MASK
    if exponent == _EXP_ALL_ONES:
        return math.copysign(math.nan if fraction else math.inf, sign)
    if exponent == 0:
        significand, scale = fraction, 1 - _BIAS - _FRACTION_BITS
    else:
        significand, scale = _HIDDEN | fraction, exponent - _BIAS - _FRACTION_BITS
    if scale < 0:
        magnitude = significand / (1 << -scale)  # int / int rounds once, also into subnormals
    else:
        try:
            magnitude = math.ldexp(float(significand), scale)
        except OverflowError:
            magnitude = math.inf  # beyond the double range: rounds to infinity, as documented
    return math.copysign(magnitude, sign)


def pack_ext(value: object, bo: str, out: bytearray) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SchemaError(f"expected a real number for an EXT, got {type(value).__name__}")
    try:
        number = float(value)  # an int is converted to the nearest float first
    except (OverflowError, TypeError, ValueError):
        raise SchemaError("value out of range for an EXT (beyond the double range)") from None
    out += _encode(number).to_bytes(16, "big" if bo == ">" else "little")


def unpack_ext(reader: Reader, bo: str) -> float:
    return _decode(int.from_bytes(reader.take(16), "big" if bo == ">" else "little"))
