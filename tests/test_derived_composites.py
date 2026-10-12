"""Composite vectors hand-derived from NI's layout rules, cross-checked by independent maths.

These shapes (1-D and 2-D DBL arrays, a 128-bit timestamp, and a mixed cluster) are NOT
worked examples on NI's "Flattened Data" page (those live, verbatim, in
``test_ni_reference.py``) and could not be captured from LabVIEW on this machine. Each vector
was written by hand from the documented rules (big-endian numbers, I32 dimension sizes,
clusters back to back, booleans one byte each) and is cross-checked here against an oracle
that does not use this library: ``struct`` for the IEEE 754 doubles and ``datetime`` for
the 1904-epoch seconds.
"""

from __future__ import annotations

import struct
from datetime import datetime, timezone

import pytest

from lvflatten import (
    DBL,
    I32,
    Array,
    BoolArray,
    Cluster,
    LVTimestamp,
    Schema,
    String,
    Timestamp,
    pack,
    unpack,
)

# The whole of 1.0, 2.0, 3.0, 4.0 and 0.25 as big-endian IEEE 754 doubles, for readability.
_D1 = "3ff0000000000000"
_D2 = "4000000000000000"
_D3 = "4008000000000000"
_D4 = "4010000000000000"
_D025 = "3fd0000000000000"

_CLUSTER_SCHEMA = Cluster([("i", I32), ("d", DBL), ("s", String()), ("b", BoolArray)])

# (name, schema, value, hand-derived hex).
_DERIVED: list[tuple[str, Schema, object, str]] = [
    ("i32_negative_19", I32, -19, "ffffffed"),
    ("dbl_array_1d", Array(DBL), [1.0, 2.0, 3.0], "00000003" + _D1 + _D2 + _D3),
    (
        "dbl_array_2d",
        Array(DBL, 2),
        [[1.0, 2.0], [3.0, 4.0]],
        "00000002" + "00000002" + _D1 + _D2 + _D3 + _D4,
    ),
    (
        "timestamp_2002",
        Timestamp,
        LVTimestamp(0xB856AC80, 0),
        "00000000b856ac80" + "0000000000000000",
    ),
    (
        "cluster_mixed",
        _CLUSTER_SCHEMA,
        {"i": -19, "d": 0.25, "s": "ABC", "b": [False, True, True, False]},
        "ffffffed" + _D025 + "00000003414243" + "00000004" + "00010100",
    ),
]

_IDS = [row[0] for row in _DERIVED]


@pytest.mark.parametrize(("_name", "schema", "value", "hexed"), _DERIVED, ids=_IDS)
def test_derived_vector_decodes_to_the_value(
    _name: str, schema: Schema, value: object, hexed: str
) -> None:
    assert unpack(schema, bytes.fromhex(hexed)) == value


@pytest.mark.parametrize(("_name", "schema", "value", "hexed"), _DERIVED, ids=_IDS)
def test_value_encodes_to_the_derived_vector(
    _name: str, schema: Schema, value: object, hexed: str
) -> None:
    assert pack(schema, value).hex() == hexed


def test_cluster_bool_array_is_one_byte_per_element() -> None:
    # The cluster ends with the bool array [F, T, T, F] as count 4 then 00 01 01 00, one byte
    # per element, the layout NI's own {T, F, T, T} example shows.
    blob = pack(_CLUSTER_SCHEMA, {"i": -19, "d": 0.25, "s": "ABC", "b": [False, True, True, False]})
    assert blob.hex().endswith("0000000400010100")


def test_doubles_cross_check_against_struct() -> None:
    for text, number in ((_D1, 1.0), (_D2, 2.0), (_D3, 3.0), (_D4, 4.0), (_D025, 0.25)):
        assert bytes.fromhex(text) == struct.pack(">d", number)


def test_timestamp_seconds_cross_check_against_datetime() -> None:
    epoch = datetime(1904, 1, 1, tzinfo=timezone.utc)
    seconds = int((datetime(2002, 1, 1, tzinfo=timezone.utc) - epoch).total_seconds())
    assert seconds == 0xB856AC80
