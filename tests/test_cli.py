import io
import json

import pytest

from lvflatten._cli import main


def test_unflatten_scalar_to_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["unflatten", "-s", "i32", "-x", "0000002a"]) == 0
    assert json.loads(capsys.readouterr().out) == 42


def test_flatten_then_unflatten_round_trips(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["flatten", "-s", "array(dbl)", "-j", "[1.0, 2.0]"]) == 0
    hex_out = capsys.readouterr().out.strip()
    assert main(["unflatten", "-s", "array(dbl)", "-x", hex_out]) == 0
    assert json.loads(capsys.readouterr().out) == [1.0, 2.0]


def test_unflatten_cluster_matches_the_documented_example(
    capsys: pytest.CaptureFixture[str],
) -> None:
    schema = "cluster(id:i32, name:string, ok:bool)"
    assert main(["unflatten", "-s", schema, "-x", "000000070000000570726f626501"]) == 0
    assert json.loads(capsys.readouterr().out) == {"id": 7, "name": "probe", "ok": True}


def test_hex_may_contain_whitespace(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["unflatten", "-s", "i16", "-x", "00 2a\n"]) == 0
    assert json.loads(capsys.readouterr().out) == 42


def test_little_endian_and_no_size(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["unflatten", "-s", "array(i16)", "-x", "01000200", "--little", "--no-size"]) == 0
    assert json.loads(capsys.readouterr().out) == [1, 2]


def test_compact_json_with_zero_indent(capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        main(["unflatten", "-s", "array(i16)", "-x", "00000003000100020003", "--indent", "0"]) == 0
    )
    assert capsys.readouterr().out.strip() == "[1, 2, 3]"


def test_timestamp_round_trips_through_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["flatten", "-s", "timestamp", "-j", "[2082844800, 0]"]) == 0
    hex_out = capsys.readouterr().out.strip()
    assert main(["unflatten", "-s", "timestamp", "-x", hex_out]) == 0
    assert json.loads(capsys.readouterr().out) == [2082844800, 0]


def test_reads_hex_from_stdin(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("0000002a"))
    assert main(["unflatten", "-s", "i32"]) == 0
    assert json.loads(capsys.readouterr().out) == 42


def test_bad_hex_reports_an_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["unflatten", "-s", "i32", "-x", "zz"]) == 1
    assert "error:" in capsys.readouterr().err


def test_truncated_data_reports_an_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["unflatten", "-s", "i32", "-x", "0000"]) == 1
    assert "error:" in capsys.readouterr().err


def test_invalid_schema_reports_an_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["unflatten", "-s", "nope", "-x", "00"]) == 1
    assert "error:" in capsys.readouterr().err


def test_invalid_json_reports_an_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["flatten", "-s", "i32", "-j", "{not json}"]) == 1
    assert "error:" in capsys.readouterr().err


def test_help_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    assert "examples:" in capsys.readouterr().out


def test_bytes_travel_as_hex_in_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["unflatten", "-s", "bytes", "-x", "00000002ff00", "--indent", "0"]) == 0
    assert json.loads(capsys.readouterr().out) == "ff00"
    assert main(["flatten", "-s", "cluster(b:bytes)", "-j", '{"b": "ff 00"}']) == 0
    assert capsys.readouterr().out.strip() == "00000002ff00"


def test_timestamp_travels_as_a_pair(capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        main(["unflatten", "-s", "array(timestamp)", "-x", "00000001" + "00" * 7 + "01" + "00" * 8])
        == 0
    )
    assert json.loads(capsys.readouterr().out) == [[1, 0]]
    assert main(["flatten", "-s", "timestamp", "-j", "[1, 0]"]) == 0
    assert capsys.readouterr().out.strip() == "00" * 7 + "01" + "00" * 8


def test_quoted_field_names(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["unflatten", "-s", 'cluster("Error Code":i32)', "-x", "ffffffed"]) == 0
    assert json.loads(capsys.readouterr().out) == {"Error Code": -19}


@pytest.mark.parametrize(
    "argv",
    [
        ["unflatten", "-s", "i32", "-x", "zz"],
        ["unflatten", "-s", "i32", "-x", "000"],
        ["unflatten", "-s", "nope", "-x", "00"],
        ["unflatten", "-s", "string", "-x", "00000001ff"],
        ["flatten", "-s", "i8", "-j", "300"],
        ["flatten", "-s", "i8", "-j", "{"],
        ["flatten", "-s", "bytes", "-j", '"xyz"'],
        ["flatten", "-s", "timestamp", "-j", "5"],
        ["flatten", "-s", "array(i32)", "-j", "[" * 100_000],
    ],
)
def test_bad_input_exits_one_with_a_message(
    argv: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(argv) == 1
    err = capsys.readouterr().err
    assert err.startswith("error: ") and len(err) < 200


def test_bad_arguments_exit_two() -> None:
    with pytest.raises(SystemExit) as info:
        main(["unflatten"])
    assert info.value.code == 2
