"""Contract tests over fixtures captured from real LabVIEW 2026.

The ``.bin`` files in ``fixtures/real_labview`` are genuine "Flatten To String" output captured
on LabVIEW 2026 (26.3.1f1) by driving shipped VIs through the ActiveX/VI Server COM interface;
``manifest.json`` records the provenance. These tests are the end-to-end promise against the
real wire format: each fixture decodes to the expected value and re-flattens to the exact bytes
on disk. They are the authoritative, LabVIEW-captured half of the suite; the documented-only
composite shapes live in ``test_documented_composites.py``.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from lvflatten import DBL, Boolean, Schema, String, pack, unpack

_FIXTURES = Path(__file__).parent / "fixtures" / "real_labview"

# (filename, schema, expected value, stated hex from the capture manifest).
# ``None`` as the expected value flags the NaN case, which is compared with math.isnan.
_REAL: list[tuple[str, Schema, object, str]] = [
    ("flatten_dbl_0p25.bin", DBL, 0.25, "3fd0000000000000"),
    ("flatten_dbl_1p0.bin", DBL, 1.0, "3ff0000000000000"),
    ("flatten_dbl_nan.bin", DBL, None, "7ff8000000000000"),
    ("flatten_dbl_posinf.bin", DBL, math.inf, "7ff0000000000000"),
    ("flatten_dbl_neginf.bin", DBL, -math.inf, "fff0000000000000"),
    ("flatten_bool_true.bin", Boolean, True, "01"),
    ("flatten_bool_false.bin", Boolean, False, "00"),
    ("flatten_string_abc.bin", String(), "ABC", "00000003414243"),
    ("flatten_string_empty.bin", String(), "", "00000000"),
]

_IDS = [row[0].removeprefix("flatten_").removesuffix(".bin") for row in _REAL]


def _read(name: str) -> bytes:
    return (_FIXTURES / name).read_bytes()


@pytest.mark.parametrize(("name", "_schema", "_value", "stated_hex"), _REAL, ids=_IDS)
def test_fixture_bytes_match_the_stated_hex(
    name: str, _schema: Schema, _value: object, stated_hex: str
) -> None:
    # Guards the fixtures themselves: the bytes on disk are exactly the captured LabVIEW output.
    assert _read(name).hex() == stated_hex


@pytest.mark.parametrize(("name", "schema", "value", "_hex"), _REAL, ids=_IDS)
def test_real_fixture_unflattens_to_the_value(
    name: str, schema: Schema, value: object, _hex: str
) -> None:
    decoded = unpack(schema, _read(name))
    if value is None:
        assert isinstance(decoded, float) and math.isnan(decoded)
    else:
        assert decoded == value


@pytest.mark.parametrize(("name", "schema", "value", "_hex"), _REAL, ids=_IDS)
def test_real_fixture_reflattens_byte_exact(
    name: str, schema: Schema, value: object, _hex: str
) -> None:
    raw = _read(name)
    source = math.nan if value is None else value
    assert pack(schema, source) == raw


def test_nan_fixture_is_the_quiet_nan_pattern() -> None:
    assert _read("flatten_dbl_nan.bin").hex() == "7ff8000000000000"
    decoded = unpack(DBL, _read("flatten_dbl_nan.bin"))
    assert isinstance(decoded, float) and math.isnan(decoded)


def test_empty_string_fixture_is_four_zero_bytes() -> None:
    raw = _read("flatten_string_empty.bin")
    assert raw == b"\x00\x00\x00\x00"
    assert unpack(String(), raw) == ""


def test_every_listed_fixture_file_exists() -> None:
    for name, _schema, _value, _hex in _REAL:
        assert (_FIXTURES / name).is_file(), name
    assert (_FIXTURES / "manifest.json").is_file()
