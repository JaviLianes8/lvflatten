"""The complete promise, proven against golden LabVIEW-flattened bytes.

Every hex string below is hand-derived from LabVIEW's documented Flatten To String format
(big-endian, I32 size prefixes), not produced by this library. Each case is asserted in both
directions, so the codec is pinned to the real wire format, not just to itself.
"""

import pytest

from lvflatten import (
    DBL,
    EXT,
    I8,
    I16,
    I32,
    I64,
    SGL,
    U8,
    U16,
    U32,
    Array,
    BoolArray,
    Boolean,
    Cluster,
    LVTimestamp,
    Schema,
    String,
    Timestamp,
    pack,
    parse_schema,
    unpack,
)

# (name, schema, value, golden-hex)
GOLDEN = [
    ("i8_negative", I8, -1, "ff"),
    ("u8_max", U8, 255, "ff"),
    ("i16_negative", I16, -2, "fffe"),
    ("u16", U16, 0x1234, "1234"),
    ("i32", I32, 42, "0000002a"),
    ("u32", U32, 0xDEADBEEF, "deadbeef"),
    ("i64", I64, 1, "0000000000000001"),
    ("sgl_one", SGL, 1.0, "3f800000"),
    ("dbl_one", DBL, 1.0, "3ff0000000000000"),
    ("ext_one", EXT, 1.0, "3fff8000000000000000000000000000"),
    ("bool_true", Boolean, True, "01"),
    ("bool_false", Boolean, False, "00"),
    ("boolarray", BoolArray, [True, False, True], "00000003a0"),
    ("string", String(), "NI", "000000024e49"),
    ("array_i32", Array(I32), [1, 2, 3], "00000003000000010000000200000003"),
    ("array_i16_2d", Array(I16, 2), [[1, 2], [3, 4]], "00000002000000020001000200030004"),
    (
        "cluster",
        Cluster([("id", I32), ("name", String()), ("ok", Boolean)]),
        {"id": 7, "name": "probe", "ok": True},
        "000000070000000570726f626501",
    ),
    (
        "timestamp_epoch",
        Timestamp,
        LVTimestamp(2082844800, 0),
        "000000007c25b0800000000000000000",
    ),
]

_IDS = [case[0] for case in GOLDEN]

# One flattened record that exercises every supported type at once.
_RECORD_SCHEMA = (
    "cluster(count:i32, temps:array(dbl), label:string, enabled:bool, "
    "flags:boolarray, stamp:timestamp, inner:cluster(x:i16, y:i16))"
)
_RECORD_VALUE = {
    "count": 2,
    "temps": [1.0, 2.0],
    "label": "ok",
    "enabled": True,
    "flags": [True, False],
    "stamp": LVTimestamp(1, 0),
    "inner": {"x": -1, "y": 1},
}
_RECORD_GOLDEN = (
    "00000002"
    "00000002" + "3ff0000000000000" + "4000000000000000"
    "00000002" + "6f6b"
    "01"
    "00000002" + "80"
    "0000000000000001" + "0000000000000000"
    "ffff" + "0001"
)


@pytest.mark.parametrize(("_name", "schema", "value", "hexed"), GOLDEN, ids=_IDS)
def test_golden_bytes_decode_to_the_value(
    _name: str, schema: Schema, value: object, hexed: str
) -> None:
    assert unpack(schema, bytes.fromhex(hexed)) == value


@pytest.mark.parametrize(("_name", "schema", "value", "hexed"), GOLDEN, ids=_IDS)
def test_value_encodes_to_the_golden_bytes(
    _name: str, schema: Schema, value: object, hexed: str
) -> None:
    assert pack(schema, value).hex() == hexed


def test_full_record_decodes_from_golden_bytes() -> None:
    schema = parse_schema(_RECORD_SCHEMA)
    assert unpack(schema, bytes.fromhex(_RECORD_GOLDEN)) == _RECORD_VALUE


def test_full_record_encodes_to_golden_bytes() -> None:
    schema = parse_schema(_RECORD_SCHEMA)
    assert pack(schema, _RECORD_VALUE).hex() == _RECORD_GOLDEN
