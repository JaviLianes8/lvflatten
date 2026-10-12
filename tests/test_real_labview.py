"""Contract tests over bytes captured from real LabVIEW 2026 (26.3.1f1, Windows x64).

Every ``.bin`` file in ``fixtures/real_labview`` came out of LabVIEW on the capture machine;
``manifest.json`` records, per file, the shipped VI and control used. Two capture routes:

- the "data string" output of shipped VIs that wrap Flatten To String (DBL, Boolean, string,
  a 32-bit integer, byte arrays), driven over ActiveX;
- front-panel datalog records of shipped example VIs (EXT, arrays, clusters, time stamp,
  U64), whose encoding was checked against Flatten To String's own output in the same run.

Each fixture must unflatten to the value LabVIEW was given and flatten back byte for byte.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from lvflatten import (
    DBL,
    EXT,
    I32,
    U8,
    U32,
    U64,
    Array,
    Boolean,
    Bytes,
    Cluster,
    LVTimestamp,
    Schema,
    String,
    Timestamp,
    pack,
    unpack,
)

_DIR = Path(__file__).parent / "fixtures" / "real_labview"
_NAN = object()  # marks the NaN cases, compared with math.isnan and the sign bit
_GRID = [[1.0, 2.0, 3.0, 4.0], [5.0, 6.0, 7.0, 8.0], [0.25, -2.5, 0.5, -1.0]]
_ERROR = Cluster([("status", Boolean), ("code", I32), ("source", String())])
_HEAD = Cluster([("text", String()), ("count", U64)])
_INPUT = Cluster([("head", _HEAD), ("grid", Array(DBL, 2)), ("error", _ERROR)])

# (file stem, schema, value LabVIEW was given)
_REAL: list[tuple[str, Schema, object]] = [
    ("dbl_0p25", DBL, 0.25),
    ("dbl_1p0", DBL, 1.0),
    ("dbl_nan", DBL, _NAN),
    ("dbl_posinf", DBL, math.inf),
    ("dbl_neginf", DBL, -math.inf),
    ("bool_true", Boolean, True),
    ("bool_false", Boolean, False),
    ("string_abc", String(), "ABC"),
    ("string_empty", String(), ""),
    ("i32_neg19", I32, -19),
    ("u32_19", U32, 19),
    ("u8_array_123", Array(U8), [1, 2, 3]),
    ("u8_array_ff0010", Bytes, b"\xff\x00\x10"),
    ("u64_19", U64, 19),
    ("ext_1p0", EXT, 1.0),
    ("ext_0p25", EXT, 0.25),
    ("ext_neg2p5", EXT, -2.5),
    ("ext_0p1", EXT, 0.1),
    ("ext_sub1em310", EXT, 1e-310),
    ("ext_posinf", EXT, math.inf),
    ("ext_negzero", EXT, -0.0),
    ("ext_max", EXT, 1.7976931348623157e308),
    ("ext_nan", EXT, _NAN),
    ("dbl_array_1d_1234", Array(DBL), [1.0, 2.0, 3.0, 4.0]),
    ("dbl_array_2d_2x4", Array(DBL, 2), _GRID[1:]),
    ("dbl_array_2d_3x4", Array(DBL, 2), _GRID),
    ("i32_array_1d", Array(I32), [2001, 2003, 2007, 2010, 2014]),
    ("i32_array_1d_shuffled", Array(I32), [2003, 2010, 2007, 2013, 2001]),
    ("bool_array_1d_tftt", Array(Boolean), [True, False, True, True]),
    ("string_array_2d_3x3", Array(String(), 2), [list("Ann"), list("Fox"), list("Nat")]),
    ("cluster_bool_i32_string", _ERROR, {"status": False, "code": -19, "source": "xyz"}),
    (
        "cluster_json_input",
        _INPUT,
        {
            "head": {"text": "ABC", "count": 19},
            "grid": _GRID,
            "error": {"status": False, "code": -19, "source": "xyz"},
        },
    ),
    ("timestamp_e6f24884", Timestamp, LVTimestamp(0xE6F24884, 0)),
]

_STEMS = [row[0] for row in _REAL]


def _read(stem: str) -> bytes:
    return (_DIR / f"flatten_{stem}.bin").read_bytes()


def _manifest() -> dict[str, str]:
    data = json.loads((_DIR / "manifest.json").read_text(encoding="utf-8"))
    return {entry["file"]: entry["bytes_hex"] for entry in data["captured_real_fixtures"]}


def test_every_fixture_on_disk_is_covered_and_listed_in_the_manifest() -> None:
    on_disk = {path.name for path in _DIR.glob("*.bin")}
    assert on_disk == {f"flatten_{stem}.bin" for stem in _STEMS}
    assert on_disk == set(_manifest())


@pytest.mark.parametrize("stem", _STEMS)
def test_fixture_bytes_match_the_manifest(stem: str) -> None:
    assert _read(stem).hex() == _manifest()[f"flatten_{stem}.bin"]


@pytest.mark.parametrize(("stem", "schema", "value"), _REAL, ids=_STEMS)
def test_real_fixture_unflattens_to_the_value(stem: str, schema: Schema, value: object) -> None:
    decoded = unpack(schema, _read(stem))
    if value is _NAN:
        assert isinstance(decoded, float) and math.isnan(decoded)
    else:
        assert decoded == value
        if isinstance(value, float):
            assert math.copysign(1.0, value) == math.copysign(1.0, decoded)  # type: ignore[arg-type]


@pytest.mark.parametrize(("stem", "schema", "value"), _REAL, ids=_STEMS)
def test_real_fixture_reflattens_byte_exact(stem: str, schema: Schema, value: object) -> None:
    raw = _read(stem)
    source = unpack(schema, raw) if value is _NAN else value
    assert pack(schema, source) == raw


def test_the_ext_layout_is_binary128_not_x87() -> None:
    # The x87 layout would put an explicit integer bit at the top of the significand.
    assert _read("ext_1p0") == bytes.fromhex("3fff") + bytes(14)


def test_the_ext_nan_capture_keeps_the_sign_of_its_double_source() -> None:
    # LabVIEW was handed the double fff8000000000000 (a negative quiet NaN).
    decoded = unpack(EXT, _read("ext_nan"))
    assert isinstance(decoded, float) and math.copysign(1.0, decoded) == -1.0


def test_the_time_stamp_capture_is_the_documented_moment() -> None:
    stamp = unpack(Timestamp, _read("timestamp_e6f24884"))
    assert isinstance(stamp, LVTimestamp)
    assert stamp.to_datetime().isoformat() == "2026-10-12T08:19:16+00:00"
