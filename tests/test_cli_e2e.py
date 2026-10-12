"""End-to-end tests that drive the real installed ``lvflatten`` console script.

These run the command as a separate process: no in-process calls, no mocks.
They use the console script installed next to the running interpreter, or else run the CLI
module in a fresh interpreter (see ``_cli_command``); either way a real process round-trip. The
fixtures are the same hand-derived golden bytes used in the contract test.
"""

import json
import re
import sys
import sysconfig
from pathlib import Path

from _cli_command import cli_command, run_cli

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
    "stamp": [1, 0],
    "inner": {"x": -1, "y": 1},
}
_RECORD_GOLDEN = (
    "00000002"
    "00000002" + "3ff0000000000000" + "4000000000000000"
    "00000002" + "6f6b"
    "01"
    "00000002" + "0100"
    "0000000000000001" + "0000000000000000"
    "ffff" + "0001"
)


def test_cli_unflattens_a_scalar() -> None:
    result = run_cli("unflatten", "-s", "i32", "-x", "0000002a")
    assert result.returncode == 0
    assert json.loads(result.stdout) == 42


def test_cli_unflattens_the_golden_record() -> None:
    result = run_cli("unflatten", "-s", _RECORD_SCHEMA, "-x", _RECORD_GOLDEN)
    assert result.returncode == 0
    assert json.loads(result.stdout) == _RECORD_VALUE


def test_cli_flattens_the_record_back_to_golden_bytes() -> None:
    result = run_cli("flatten", "-s", _RECORD_SCHEMA, "-j", json.dumps(_RECORD_VALUE))
    assert result.returncode == 0
    assert result.stdout.strip() == _RECORD_GOLDEN


def test_cli_reads_hex_from_stdin() -> None:
    result = run_cli("unflatten", "-s", "string", stdin="00000002 4e49")
    assert result.returncode == 0
    assert json.loads(result.stdout) == "NI"


def test_cli_reports_truncated_data_on_stderr_with_exit_one() -> None:
    result = run_cli("unflatten", "-s", "i32", "-x", "0000")
    assert result.returncode == 1
    assert "error:" in result.stderr


def test_cli_version_prints_the_number() -> None:
    result = run_cli("--version")
    assert result.returncode == 0
    pyproject = (Path(__file__).resolve().parent.parent / "pyproject.toml").read_text("utf-8")
    version = re.search(r'^version = "([^"]+)"$', pyproject, re.MULTILINE)
    assert version is not None
    assert result.stdout.strip() == f"lvflatten {version.group(1)}"


def test_cli_under_test_belongs_to_this_interpreter() -> None:
    command = cli_command()
    if command[0] != sys.executable:
        scripts = Path(sysconfig.get_path("scripts")).resolve()
        assert Path(command[0]).resolve().parent == scripts
