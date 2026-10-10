"""Known-byte vectors cross-checked against NI's "Flattened Data" documentation.

LabVIEW flattens numbers big-endian, prepends an I32 length to strings and arrays, and lays
cluster fields out back to back with no padding. These fixed expectations guard the wire
format, not just the round-trip.
"""

from lvflatten import (
    DBL,
    I16,
    I32,
    SGL,
    U8,
    U32,
    Array,
    Boolean,
    Cluster,
    String,
    pack,
)


def test_i32_five_is_big_endian() -> None:
    assert pack(I32, 5) == b"\x00\x00\x00\x05"


def test_u8_vector() -> None:
    assert pack(U8, 0xAB) == b"\xab"


def test_i16_negative_one_is_twos_complement() -> None:
    assert pack(I16, -1) == b"\xff\xff"


def test_u32_vector() -> None:
    assert pack(U32, 0x01020304) == b"\x01\x02\x03\x04"


def test_double_one_is_ieee754() -> None:
    assert pack(DBL, 1.0) == b"\x3f\xf0\x00\x00\x00\x00\x00\x00"


def test_single_one_is_ieee754() -> None:
    assert pack(SGL, 1.0) == b"\x3f\x80\x00\x00"


def test_boolean_true_vector() -> None:
    assert pack(Boolean, True) == b"\x01"


def test_string_vector() -> None:
    assert pack(String(), "NI") == b"\x00\x00\x00\x02NI"


def test_double_array_vector() -> None:
    # I32 count 2, then two IEEE 754 doubles (1.0 and 2.0).
    expected = (
        b"\x00\x00\x00\x02"
        + b"\x3f\xf0\x00\x00\x00\x00\x00\x00"
        + b"\x40\x00\x00\x00\x00\x00\x00\x00"
    )
    assert pack(Array(DBL), [1.0, 2.0]) == expected


def test_cluster_vector() -> None:
    schema = Cluster([("count", I32), ("label", String())])
    assert pack(schema, {"count": 1, "label": "x"}) == b"\x00\x00\x00\x01\x00\x00\x00\x01x"
