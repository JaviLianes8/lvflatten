"""Command-line entry point: unflatten hex to JSON, or flatten JSON back to hex."""

from __future__ import annotations

import argparse
import binascii
import json
import sys
from collections.abc import Sequence

from . import __version__
from ._codec import pack, unpack
from ._errors import LVFlattenError
from ._json import from_jsonable
from ._parse import parse_schema

_EXAMPLES = """\
examples:
  # unflatten a big-endian I32 to JSON
  lvflatten unflatten -s i32 -x 0000002a

  # unflatten a cluster
  lvflatten unflatten -s "cluster(id:i32, name:string, ok:bool)" -x 000000070000000570726f626501

  # flatten JSON back to hex
  lvflatten flatten -s "array(dbl)" -j "[1.0, 2.0]"

  # little-endian, and drop the top-level size prefix
  lvflatten unflatten -s "array(i16)" -x 01000200 --little --no-size

Schema text: scalars i8..i64 u8..u64 sgl dbl ext bool boolarray timestamp,
plus string[(encoding)], array(<schema>[, ndims]) and cluster(name:<schema>, ...).
Hex may contain spaces or newlines; with -x/-j omitted the input is read from stdin.
"""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lvflatten",
        description="Encode and decode LabVIEW Flatten To String data from the shell.",
        epilog=_EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"lvflatten {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    decode = sub.add_parser("unflatten", help="decode hex bytes to JSON")
    decode.add_argument("-s", "--schema", required=True, help="schema text, e.g. 'cluster(id:i32)'")
    decode.add_argument("-x", "--hex", help="hex input; read from stdin when omitted")
    decode.add_argument("--indent", type=int, default=2, help="JSON indent (0 for compact)")
    _add_common(decode)

    encode = sub.add_parser("flatten", help="encode JSON to hex bytes")
    encode.add_argument("-s", "--schema", required=True, help="schema text, e.g. 'array(dbl)'")
    encode.add_argument("-j", "--json", help="JSON input; read from stdin when omitted")
    _add_common(encode)
    return parser


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--little", action="store_true", help="little-endian (default big-endian)")
    parser.add_argument("--no-size", action="store_true", help="drop the top-level size prefix")


def _run_unflatten(args: argparse.Namespace) -> int:
    schema = parse_schema(args.schema)
    raw = args.hex if args.hex is not None else sys.stdin.read()
    data = binascii.unhexlify("".join(raw.split()))
    value = unpack(schema, data, byte_order=_order(args), prepend_size=not args.no_size)
    print(json.dumps(value, indent=args.indent if args.indent > 0 else None))
    return 0


def _run_flatten(args: argparse.Namespace) -> int:
    schema = parse_schema(args.schema)
    text = args.json if args.json is not None else sys.stdin.read()
    value = from_jsonable(schema, json.loads(text))
    data = pack(schema, value, byte_order=_order(args), prepend_size=not args.no_size)
    print(data.hex())
    return 0


def _order(args: argparse.Namespace) -> str:
    return "little" if args.little else "big"


def main(argv: Sequence[str] | None = None) -> int:
    """Parse the arguments and run the chosen command, returning a process exit code."""
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "unflatten":
            return _run_unflatten(args)
        return _run_flatten(args)
    except (LVFlattenError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
