"""Real end-to-end test: drive the installed ``lvflatten`` console script over real fixtures.

It shells out to the console script installed next to the interpreter running the tests
(never whatever is first on PATH) and feeds it the exact bytes captured from LabVIEW 2026.
Without an installed script it runs the CLI module of the package under test in a fresh
interpreter. No mocks, and the tests never install anything.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
from _cli_command import run_cli

import lvflatten

_FIXTURES = Path(__file__).parent / "fixtures" / "real_labview"

# (filename, schema text, expected JSON-decoded value). None flags the NaN case.
_CASES: list[tuple[str, str, object]] = [
    ("flatten_dbl_0p25.bin", "dbl", 0.25),
    ("flatten_dbl_1p0.bin", "dbl", 1.0),
    ("flatten_dbl_nan.bin", "dbl", None),
    ("flatten_dbl_posinf.bin", "dbl", math.inf),
    ("flatten_dbl_neginf.bin", "dbl", -math.inf),
    ("flatten_bool_true.bin", "bool", True),
    ("flatten_bool_false.bin", "bool", False),
    ("flatten_string_abc.bin", "string", "ABC"),
    ("flatten_string_empty.bin", "string", ""),
    ("flatten_u8_array_ff0010.bin", "bytes", "ff0010"),
    ("flatten_ext_neg2p5.bin", "ext", -2.5),
    ("flatten_timestamp_e6f24884.bin", "timestamp", [0xE6F24884, 0]),
    (
        "flatten_string_array_2d_3x3.bin",
        "array(string, 2)",
        [list("Ann"), list("Fox"), ["N", "a", "t"]],
    ),
    (
        "flatten_cluster_bool_i32_string.bin",
        'cluster(status:bool, code:i32, "error source":string)',
        {"status": False, "code": -19, "error source": "xyz"},
    ),
]

_IDS = [row[0].removeprefix("flatten_").removesuffix(".bin") for row in _CASES]


@pytest.mark.parametrize(("name", "schema", "value"), _CASES, ids=_IDS)
def test_installed_cli_unflattens_real_fixture(name: str, schema: str, value: object) -> None:
    raw_hex = (_FIXTURES / name).read_bytes().hex()
    result = run_cli("unflatten", "-s", schema, "-x", raw_hex)
    assert result.returncode == 0, result.stderr
    decoded = json.loads(result.stdout)
    if value is None:
        assert isinstance(decoded, float) and math.isnan(decoded)
    else:
        assert decoded == value


def test_installed_cli_reports_this_source_version() -> None:
    result = run_cli("--version")
    assert result.returncode == 0
    assert result.stdout.strip() == f"lvflatten {lvflatten.__version__}"


@pytest.mark.parametrize(("name", "schema", "value"), _CASES, ids=_IDS)
def test_installed_cli_reflattens_real_fixture(name: str, schema: str, value: object) -> None:
    raw_hex = (_FIXTURES / name).read_bytes().hex()
    decoded = run_cli("unflatten", "-s", schema, "-x", raw_hex, "--indent", "0")
    encoded = run_cli("flatten", "-s", schema, f"--json={decoded.stdout}")
    assert encoded.returncode == 0, encoded.stderr
    assert encoded.stdout.strip() == raw_hex


def test_installed_cli_reads_stdin_and_fails_cleanly() -> None:
    piped = run_cli("unflatten", "-s", "i32", stdin="ffff ffed\n")
    assert piped.returncode == 0 and json.loads(piped.stdout) == -19
    bad = run_cli("unflatten", "-s", "i32", "-x", "ffff")
    assert bad.returncode == 1
    assert bad.stderr.startswith("error: need 4 bytes")
    assert "Traceback" not in bad.stderr
    usage = run_cli("unflatten")
    assert usage.returncode == 2


def test_installed_cli_roundtrips_string_fixture() -> None:
    raw_hex = (_FIXTURES / "flatten_string_abc.bin").read_bytes().hex()
    decoded = run_cli("unflatten", "-s", "string", "-x", raw_hex)
    assert decoded.returncode == 0
    assert json.loads(decoded.stdout) == "ABC"
    encoded = run_cli("flatten", "-s", "string", "-j", '"ABC"')
    assert encoded.returncode == 0
    assert encoded.stdout.strip() == raw_hex
