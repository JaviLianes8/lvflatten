# lvflatten guide

This guide covers every public name in `lvflatten` 1.0. All Python blocks below are run by
the test suite, so they stay correct.

## 1. The model

LabVIEW's Flatten To String writes a value's bytes and nothing else: no type tag, no field
names. To read those bytes you must say what type they hold. In `lvflatten` that is a
**schema**: a small tree of nodes that mirrors the LabVIEW type.

```python
from lvflatten import I32, Schema, pack, unpack

assert pack(I32, 42) == b"\x00\x00\x00\x2a"
assert unpack(I32, b"\x00\x00\x00\x2a") == 42
assert isinstance(I32, Schema)  # every node derives from Schema
```

`pack(schema, value)` returns `bytes`. `unpack(schema, data)` returns the Python value and
requires the whole buffer to be consumed; `unpack_from` (section 3) reads one value from the
middle of a longer buffer.

`unpack` is typed to return `object`, because the type depends on the schema. Under a strict
type checker, narrow it with `isinstance` or `typing.cast`:

```python
from typing import cast

from lvflatten import I32, Cluster, String, pack, unpack

count = cast(int, unpack(I32, pack(I32, 41))) + 1
record = cast(dict[str, object], unpack(Cluster({"s": String()}), pack(String(), "x")))
assert count == 42 and record == {"s": "x"}
```

## 2. Schema nodes

### Scalars (ready-made singletons)

| Node | Python value | Bytes |
| --- | --- | --- |
| `I8 I16 I32 I64` | `int` | 1, 2, 4, 8, signed |
| `U8 U16 U32 U64` | `int` | 1, 2, 4, 8, unsigned |
| `SGL`, `DBL` | `float` | 4, 8 (IEEE 754) |
| `EXT` | `float` | 16 |
| `Boolean` | `bool` | 1 |
| `Timestamp` | `LVTimestamp` | 16 |
| `Bytes` | `bytes` | 4 + length |

Integers refuse `bool` and out-of-range values. Floats accept `int` or `float`. Values must
be the plain Python types (or subclasses of them): convert NumPy scalars with `.item()`
first. On decode a
Boolean is TRUE for any nonzero byte, as NI documents; on encode TRUE is always `01`.

```python
from lvflatten import DBL, EXT, SGL, U16, Boolean, pack, unpack

assert pack(U16, 0x1234) == b"\x12\x34"
assert pack(SGL, 1.0).hex() == "3f800000"
assert pack(DBL, 0.25).hex() == "3fd0000000000000"
assert unpack(EXT, pack(EXT, 1.5)) == 1.5
assert unpack(Boolean, b"\x02") is True
```

`EXT` is flattened as 16 bytes in the IEEE 754 binary128 layout (sign, 15-bit exponent
biased by 16383, 112-bit fraction with an implicit leading one), as real LabVIEW 2026 output
shows: 1.0 is `3fff` followed by fourteen zero bytes. An `int` is first converted to the
nearest `float`. Every Python `float` encodes exactly,
keeping signed zero, infinities and the NaN sign; decoding rounds to the nearest double, so
magnitudes beyond the double range become infinity and very small ones become zero.

### Strings and bytes

`String(encoding="utf-8")` is an I32 byte count followed by the encoded text. The encoding
is any Python codec name, checked when the node is built and kept under its canonical name
(`String("UTF8") == String()`, `String("latin-1").encoding == "iso8859-1"`). LabVIEW on Windows writes
text in the system ANSI code page, so use `String("cp1252")` (or your code page) for
non-ASCII text from a Western Windows machine. `Bytes` has the same wire form but keeps the
data as `bytes`, for LabVIEW strings used as byte buffers.

```python
from lvflatten import Bytes, String, pack, unpack

assert pack(String(), "ABC").hex() == "00000003414243"
assert unpack(String("cp1252"), bytes.fromhex("00000001e9")) == "é"
assert unpack(Bytes, bytes.fromhex("00000002ff00")) == b"\xff\x00"
```

### Arrays

`Array(element, ndims=1)` writes one I32 size per dimension, slowest-varying first, then the
elements in row-major order. The value is a list nested `ndims` deep (tuples are accepted on
encode); rows must all have the same length. `BoolArray` is a ready-made `Array(Boolean)`.

```python
from lvflatten import I8, Array, BoolArray, pack, unpack

grid = Array(I8, 2)
assert pack(grid, [[1, 2, 3], [4, 5, 6]]).hex() == "0000000200000003010203040506"
assert unpack(grid, pack(grid, [[1, 2, 3], [4, 5, 6]])) == [[1, 2, 3], [4, 5, 6]]
assert pack(BoolArray, [True, False, True, True]).hex() == "0000000401000101"
```

### Clusters

`Cluster(fields)` takes `(name, schema)` pairs or a dict, in LabVIEW cluster order. Names
must be unique strings. The value is a mapping; extra keys are ignored and a missing key is
an error. Unpack returns a `dict` in field order.

```python
from lvflatten import I16, Cluster, String, pack, unpack

point = Cluster({"label": String(), "x": I16})
blob = pack(point, {"label": "ABC", "x": 4})
assert blob.hex() == "000000034142430004"
assert unpack(point, blob) == {"label": "ABC", "x": 4}
```

LabVIEW clusters may hold unlabelled or duplicate labels; give them unique names here, in
order. The names never reach the wire.

### Time stamps

`Timestamp` holds an `LVTimestamp(seconds, fraction)`: signed whole seconds since
1904-01-01T00:00:00Z and an unsigned 2**-64 second fraction, exactly as LabVIEW stores them.
`LVTimestamp.from_datetime` and `to_datetime` convert to and from timezone-aware datetimes.

```python
from datetime import datetime, timezone

from lvflatten import LVTimestamp, Timestamp, pack, unpack

moment = datetime(2026, 10, 12, 8, 30, 15, 250000, tzinfo=timezone.utc)
stamp = LVTimestamp.from_datetime(moment)
assert stamp.fraction == 1 << 62  # a quarter of a second
assert unpack(Timestamp, pack(Timestamp, stamp)).to_datetime() == moment
```

## 3. Options

Both `pack` and `unpack` take two keyword-only options:

- `byte_order`: `"big"` (the default, as LabVIEW) or `"little"`.
  With `"little"`, every number is byte-swapped on its own. A time stamp is written as
  its seconds (I64) then its fraction (U64), each little-endian; an EXT is the whole
  16-byte value reversed. Big-endian output is checked against LabVIEW 2026; these two
  little-endian layouts are not, as no capture of them was possible.
- `prepend_size`: `True` by default. `False` drops the size of a top-level string, `Bytes`
  or array, like LabVIEW's "prepend array or string size?" input. Nested sizes are always
  kept. On unpack, `False` works for strings, `Bytes`, and one-dimensional arrays of
  fixed-size elements, which are read to the end of the buffer.

```python
from lvflatten import I32, U16, Array, String, pack, unpack

assert pack(U16, 0x1234, byte_order="little") == b"\x34\x12"
assert pack(String(), "ABC", prepend_size=False) == b"ABC"
assert unpack(Array(I32), bytes.fromhex("0000000100000002"), prepend_size=False) == [1, 2]
```

`prepend_size` must be a real `bool`; anything else raises `SchemaError`.

### Several values back to back

`unpack_from(schema, data, offset=0, *, byte_order="big")` reads one value starting at
`offset` and returns `(value, next_offset)`, leaving any following bytes alone. It mirrors
the "rest of the flattened string" output of LabVIEW's Unflatten From String and is the way
to walk a buffer or TCP stream holding several flattened values. Sizes are always read from
the data, so it has no `prepend_size` option.

```python
from lvflatten import I16, Cluster, String, pack, unpack_from

record = Cluster([("n", I16), ("s", String())])
stream = pack(record, {"n": 1, "s": "a"}) + pack(record, {"n": 2, "s": "bc"})
offset, values = 0, []
while offset < len(stream):
    value, offset = unpack_from(record, stream, offset)
    values.append(value)
assert values == [{"n": 1, "s": "a"}, {"n": 2, "s": "bc"}]
```

## 4. Errors

Every deliberate error derives from `LVFlattenError`, and every one of those is also a
`ValueError`.

| Error | Raised when |
| --- | --- |
| `SchemaError` | the schema, an option, or the Python value does not fit the type |
| `DataError` | the bytes do not fit the schema (negative size, bad text, ...) |
| `TruncatedDataError` (a `DataError`) | the bytes end before the value does |
| `TrailingDataError` (a `DataError`) | bytes are left over; `.count` says how many |

`LVTimestamp.from_datetime` raises `SchemaError` for a naive datetime, and `to_datetime`
raises `DataError` for a time stamp outside the years 1 to 9999. A `String` encoding must be a
text codec (`"hex"` or `"zlib"` raise `SchemaError`). Passing something that is not
bytes-like as `data` raises `TypeError`, as does calling `Schema()` itself. Messages never echo
the value being packed, and anything quoted from the input is cut to a few dozen characters.

```python
from lvflatten import I32, DataError, SchemaError, TrailingDataError, pack, unpack

try:
    unpack(I32, b"\x00\x00\x00\x01\xff")
except TrailingDataError as exc:
    assert exc.count == 1 and isinstance(exc, DataError)

try:
    pack(I32, 2**40)
except SchemaError as exc:
    assert "out of range" in str(exc)
```

Decoding is safe on untrusted input. Work is linear in the input size, and size headers that
claim more data than exists fail at once. Objects that cost no input bytes (the rows of an
array with a zero dimension, and the dicts of an array of empty clusters, counted through
every nesting level) share a budget of 1024 plus one per input byte; beyond it `DataError`
is raised. For `unpack_from` the input bytes are only those the value has read, so bytes
further along a stream cannot be borrowed. `pack` has no such limit, so a value with more
than about a thousand empty rows or empty clusters (for example a 2000 x 0 array) packs but
is refused by `unpack`; it is the price of a hard bound on what hostile bytes can cost.
Everything else the decoder builds consumes
input, so memory grows linearly with the data, by a factor fixed by the schema rather than
by the bytes. An array has at most 64 dimensions.

`data` may be any object supporting the buffer protocol: `bytes`, `bytearray`, `memoryview`,
`array.array`, `mmap` and so on. `unpack_from` reads it in place (a strided view of single
bytes too), so walking a long buffer stays linear, and releases it before returning or
raising, so a `bytearray` can grow inside the `except` block that caught a
`TruncatedDataError`. Other non-contiguous layouts (a strided view of wider items, a
Fortran-ordered array) are copied on every call: convert them with `bytes()` once before
walking them with `unpack_from`.

Schemas are ordinary immutable values: they compare by value, hash, copy and pickle (so they
can be sent to worker processes). A schema nested thousands of levels deep is refused by the
text form and by `pack`, `unpack` and `format_schema` with `SchemaError`, but Python's own
`repr`, `hash`, `copy.deepcopy` and `pickle` of such an object may hit the interpreter's
recursion limit. `TrailingDataError` pickles with its `count`.

## 5. The schema text form

`parse_schema(text)` reads a compact text form and `format_schema(schema)` writes it back.

```
i32 | dbl | bool | timestamp | bytes | ...   scalars, case-insensitive
string  |  string(cp1252)                    a string, optional encoding
array(dbl)  |  array(i16, 2)                 an array, optional dimension count
cluster(id:i32, "Error Code":i32)            a cluster; quote names with other characters
```

Bare names are letters, digits, `_`, `-` and `.`; other names go in double quotes, where a
backslash escapes `"` or a backslash. `boolarray` is read as `array(bool)`. Nesting deeper
than 64 levels is refused.

```python
from lvflatten import I32, Array, BoolArray, Cluster, format_schema, parse_schema

schema = parse_schema('cluster("Error Code":i32, flags:boolarray, grid:array(i32, 2))')
assert schema == Cluster([("Error Code", I32), ("flags", BoolArray), ("grid", Array(I32, 2))])
assert format_schema(schema) == 'cluster("Error Code":i32, flags:array(bool), grid:array(i32, 2))'
assert parse_schema(format_schema(schema)) == schema
```

## 6. Command line

The `lvflatten` command turns hex into JSON and JSON into hex.

```
lvflatten unflatten -s SCHEMA [-x HEX] [--indent N] [--little] [--no-size]
lvflatten flatten   -s SCHEMA [-j JSON] [--little] [--no-size]
lvflatten --version
```

With `-x` or `-j` omitted the input comes from standard input; hex may contain spaces and
newlines. In JSON a time stamp is `[seconds, fraction]` and `Bytes` is a hex string. NaN and
infinities are written as `NaN`, `Infinity` and `-Infinity`. A JSON value that starts with `-` but is not a
plain number (such as `-Infinity`) must be attached to its option, `--json=-Infinity`, or
piped in on standard input. The exit status is 0 on success,
1 for bad data or a bad schema (with a one-line `error:` message on standard error), and 2 for
bad arguments.

```
$ lvflatten unflatten -s "array(i16)" -x 01000200 --little --no-size
[
  1,
  2
]
```

## 7. Stability

From 1.0.0 the public API is the list in `lvflatten.__all__`, and it follows semantic
versioning: no name, signature, default or error class changes before 2.0. The documented
attributes of the nodes (`String.encoding`, `Array.element`, `Array.ndims`, `Cluster.fields`)
are part of it. Modules whose name starts with an underscore, and the classes of the scalar
singletons, are internal. Error message wording is not part of the API.
