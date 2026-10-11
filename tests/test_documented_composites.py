"""Composite golden vectors derived from NI documentation, not captured from LabVIEW.

These shapes (an I32, a 1-D and a 2-D DBL array, a 128-bit timestamp, and a mixed cluster)
could not be captured on the fixture machine: LabVIEW VI Scripting is not reachable over the
ActiveX/VI Server COM interface, so no VI exposing a settable control of these types could be
built headlessly. Their expected bytes therefore come from NI's "Flattened Data" reference and
are labeled honestly as documentation-derived, in contrast to the LabVIEW-captured fixtures in
``test_real_labview.py``. Every vector is asserted in both directions against the documented
bytes, so the codec is pinned to the reference wire format and not merely to itself.
"""

from __future__ import annotations

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

# (name, schema, value, NI-documented hex).
_DOCUMENTED: list[tuple[str, Schema, object, str]] = [
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
        LVTimestamp(0xB8555B00, 0),
        "00000000b8555b00" + "0000000000000000",
    ),
    (
        "cluster_mixed",
        _CLUSTER_SCHEMA,
        {"i": -19, "d": 0.25, "s": "ABC", "b": [False, True, True, False]},
        "ffffffed" + _D025 + "00000003414243" + "00000004" + "00010100",
    ),
]

_IDS = [row[0] for row in _DOCUMENTED]


@pytest.mark.parametrize(("_name", "schema", "value", "hexed"), _DOCUMENTED, ids=_IDS)
def test_documented_vector_decodes_to_the_value(
    _name: str, schema: Schema, value: object, hexed: str
) -> None:
    assert unpack(schema, bytes.fromhex(hexed)) == value


@pytest.mark.parametrize(("_name", "schema", "value", "hexed"), _DOCUMENTED, ids=_IDS)
def test_value_encodes_to_the_documented_vector(
    _name: str, schema: Schema, value: object, hexed: str
) -> None:
    assert pack(schema, value).hex() == hexed


def test_cluster_bool_array_is_one_byte_per_element() -> None:
    # The documented cluster ends with the bool array [F, T, T, F] as count 4 then 00 01 01 00,
    # one byte per element. This is the layout the real-vs-documented round exposed and fixed.
    blob = pack(_CLUSTER_SCHEMA, {"i": -19, "d": 0.25, "s": "ABC", "b": [False, True, True, False]})
    assert blob.hex().endswith("0000000400010100")
