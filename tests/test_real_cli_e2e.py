"""Real end-to-end test: drive the installed ``lvflatten`` console script over real fixtures.

This is the most honest end-to-end check available: it shells out to the console script that an
editable install puts on PATH and feeds it the exact bytes captured from LabVIEW 2026. No
package import, no mocks, no module fallback. If the console script is missing, the session
fixture installs the project editable once so the test drives the genuine entry point.
"""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

import lvflatten

_ROOT = Path(__file__).parent.parent
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


@pytest.fixture(scope="session")
def console_script() -> Iterator[str]:
    exe = shutil.which("lvflatten")
    if exe is None:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", ".", "--quiet"],
            cwd=_ROOT,
            check=True,
        )
        exe = shutil.which("lvflatten")
    if exe is None:
        pytest.fail("the lvflatten console script is not on PATH after an editable install")
    yield exe


def _run(exe: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([exe, *args], capture_output=True, text=True)


@pytest.mark.parametrize(("name", "schema", "value"), _CASES, ids=_IDS)
def test_installed_cli_unflattens_real_fixture(
    console_script: str, name: str, schema: str, value: object
) -> None:
    raw_hex = (_FIXTURES / name).read_bytes().hex()
    result = _run(console_script, "unflatten", "-s", schema, "-x", raw_hex)
    assert result.returncode == 0, result.stderr
    decoded = json.loads(result.stdout)
    if value is None:
        assert isinstance(decoded, float) and math.isnan(decoded)
    else:
        assert decoded == value


def test_installed_cli_reports_this_source_version(console_script: str) -> None:
    result = _run(console_script, "--version")
    assert result.returncode == 0
    assert result.stdout.strip() == f"lvflatten {lvflatten.__version__}"


@pytest.mark.parametrize(("name", "schema", "value"), _CASES, ids=_IDS)
def test_installed_cli_reflattens_real_fixture(
    console_script: str, name: str, schema: str, value: object
) -> None:
    raw_hex = (_FIXTURES / name).read_bytes().hex()
    decoded = _run(console_script, "unflatten", "-s", schema, "-x", raw_hex, "--indent", "0")
    encoded = _run(console_script, "flatten", "-s", schema, f"--json={decoded.stdout}")
    assert encoded.returncode == 0, encoded.stderr
    assert encoded.stdout.strip() == raw_hex


def test_installed_cli_reads_stdin_and_fails_cleanly(console_script: str) -> None:
    piped = subprocess.run(
        [console_script, "unflatten", "-s", "i32"],
        input="ffff ffed\n",
        capture_output=True,
        text=True,
    )
    assert piped.returncode == 0 and json.loads(piped.stdout) == -19
    bad = _run(console_script, "unflatten", "-s", "i32", "-x", "ffff")
    assert bad.returncode == 1
    assert bad.stderr.startswith("error: need 4 bytes")
    assert "Traceback" not in bad.stderr
    usage = _run(console_script, "unflatten")
    assert usage.returncode == 2


def test_installed_cli_roundtrips_string_fixture(console_script: str) -> None:
    raw_hex = (_FIXTURES / "flatten_string_abc.bin").read_bytes().hex()
    decoded = _run(console_script, "unflatten", "-s", "string", "-x", raw_hex)
    assert decoded.returncode == 0
    assert json.loads(decoded.stdout) == "ABC"
    encoded = _run(console_script, "flatten", "-s", "string", "-j", '"ABC"')
    assert encoded.returncode == 0
    assert encoded.stdout.strip() == raw_hex
