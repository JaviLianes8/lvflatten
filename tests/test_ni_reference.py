"""Every worked example in NI's "Flattened Data" reference, copied from the page as fetched.

Source: https://www.ni.com/docs/en-US/bundle/labview/page/flattened-data.html
(fetched 2026-10-12 through https://docs-be.ni.com/api/bundle/labview/page/flattened-data.html,
the JSON backend the page loads its text from). The quoted sentence next to each vector is
the page's own wording; the hex is the page's hex with the spaces removed. Nothing here was
produced by this library. The path example on the same page is not covered because paths
are outside this codec's scope.
"""

from __future__ import annotations

import pytest

from lvflatten import DBL, I8, I16, I32, Array, Boolean, Cluster, Schema, String, pack, unpack

# (quote from the page, schema, value, hex from the page)
_NI: list[tuple[str, Schema, object, str]] = [
    (
        "a 32-bit integer with a value of -19 is flattened to FFFF FFED",
        I32,
        -19,
        "FFFF FFED",
    ),
    (
        "A double-precision floating-point number with a value equal to 1/4 is flattened to "
        "3FD0 0000 0000 0000",
        DBL,
        0.25,
        "3FD0 0000 0000 0000",
    ),
    ("A Boolean value of FALSE is 00", Boolean, False, "00"),
    (
        "a string type with value ABC is flattened to 0000 0003 4142 43",
        String(),
        "ABC",
        "0000 0003 4142 43",
    ),
    (
        "{ {1, 2, 3}, {4, 5, 6} } is flattened to 0000 0002 0000 0003 0102 0304 0506",
        Array(I8, 2),
        [[1, 2, 3], [4, 5, 6]],
        "0000 0002 0000 0003 0102 0304 0506",
    ),
    (
        "{T, F, T, T} is flattened to 0000 0004 0100 0101",
        Array(Boolean),
        [True, False, True, True],
        "0000 0004 0100 0101",
    ),
    (
        "a flattened cluster of a 16-bit integer of value 4 (decimal) and a 32-bit integer of "
        "value 12 is 0004 0000 000C",
        Cluster([("a", I16), ("b", I32)]),
        {"a": 4, "b": 12},
        "0004 0000 000C",
    ),
    (
        "A flattened cluster of a string ABC and a 16-bit integer of value 4 is "
        "0000 0003 4142 4300 04",
        Cluster([("s", String()), ("n", I16)]),
        {"s": "ABC", "n": 4},
        "0000 0003 4142 4300 04",
    ),
    (
        "A flattened cluster of a 16-bit integer of value 7, a cluster of a 16-bit integer of "
        "value 8, and a 16-bit integer of value 9 is 0007 0008 0009",
        Cluster([("a", I16), ("inner", Cluster([("b", I16)])), ("c", I16)]),
        {"a": 7, "inner": {"b": 8}, "c": 9},
        "0007 0008 0009",
    ),
]

_IDS = [f"ni{index}" for index in range(len(_NI))]


def _bytes(spaced_hex: str) -> bytes:
    return bytes.fromhex(spaced_hex.replace(" ", ""))


@pytest.mark.parametrize(("_quote", "schema", "value", "hexed"), _NI, ids=_IDS)
def test_ni_example_unflattens_to_the_documented_value(
    _quote: str, schema: Schema, value: object, hexed: str
) -> None:
    assert unpack(schema, _bytes(hexed)) == value


@pytest.mark.parametrize(("_quote", "schema", "value", "hexed"), _NI, ids=_IDS)
def test_ni_example_flattens_to_the_documented_bytes(
    _quote: str, schema: Schema, value: object, hexed: str
) -> None:
    assert pack(schema, value) == _bytes(hexed)


@pytest.mark.parametrize("byte", [1, 2, 0x7F, 0x80, 0xFF])
def test_any_nonzero_byte_is_true(byte: int) -> None:
    # "A Boolean value of TRUE is any nonzero value." and "The preferred value for TRUE is 01."
    assert unpack(Boolean, bytes([byte])) is True
    assert pack(Boolean, True) == b"\x01"


def test_flattened_numbers_are_big_endian_by_default() -> None:
    # "LabVIEW stores flattened numeric data in big-endian form (most significant byte first)"
    assert pack(I32, 0x01020304) == b"\x01\x02\x03\x04"
