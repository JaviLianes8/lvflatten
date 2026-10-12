# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-12

The first stable release. The public API is exactly `lvflatten.__all__` and follows semantic
versioning from here on: names, signatures, defaults and error classes stay put until 2.0.
Stable in 1.0: `pack` and `unpack` with `byte_order` and `prepend_size`; the schema nodes
`I8` to `U64`, `SGL`, `DBL`, `EXT`, `Boolean`, `String`, `Bytes`, `Array`, `BoolArray`,
`Cluster`, `Timestamp` and the `Schema` base class; `LVTimestamp`; `parse_schema` and
`format_schema`; the error classes; and the `lvflatten` command line.

### Changed (with migration notes)

- **`EXT` now uses the IEEE 754 binary128 layout LabVIEW really writes.** Real LabVIEW 2026
  output shows an extended number flattens as sign, 15-bit exponent and a 112-bit fraction
  with an implicit leading one (1.0 is `3fff` then fourteen zero bytes). Every 0.x release
  wrote the x87 80-bit layout with an explicit integer bit (1.0 was `3fff8000...`), which
  LabVIEW reads as a different number. Migration: every `EXT` byte sequence changes; bytes
  written by 0.x for `EXT` must be decoded with 0.x and re-encoded with 1.0. Encoding is
  exact for every Python `float`, including signed zero, infinities and the NaN sign.
- **Data errors have their own class.** Bytes that do not fit the schema now raise
  `DataError` (a new `LVFlattenError` subclass) instead of `SchemaError`: negative string,
  array or dimension sizes, text that does not decode, and a buffer that is not a whole
  number of elements with `prepend_size=False`. `TruncatedDataError` is now a subclass of
  `DataError`. Migration: catch `DataError` (or `LVFlattenError`) where you caught
  `SchemaError` around `unpack`.
- **Trailing bytes raise `TrailingDataError`** (a `DataError`, with a `count` attribute)
  instead of a bare `LVFlattenError`. Code catching `LVFlattenError` is unaffected.
- **`SchemaError` and `DataError` are also `ValueError`s**, so `except ValueError` catches
  them.
- **`BoolArray` is now exactly `Array(Boolean)`**, which has produced the same bytes since
  0.3.0. `format_schema` writes it as `array(bool)`; `boolarray` is still accepted by
  `parse_schema`. The internal `BoolArrayType` class is gone. As a side effect,
  `pack(BoolArray, ..., prepend_size=False)` now drops the count like any other top-level
  array (0.3.0 kept it).
- **`Schema` is a base class** instead of a `typing` union. `isinstance(x, Schema)` behaves
  as before, every node has a docstring, and annotations using `Schema` keep working. `Schema()` itself
  cannot be instantiated (`TypeError`).
- **`byte_order` is typed as `Literal["big", "little"]`.** Runtime behaviour is unchanged;
  type checkers now flag other strings. A variable typed as plain `str` needs a `Literal`
  annotation or a cast.
- **`prepend_size` must be a `bool`.** 0.x treated any truthy or falsy value as the flag;
  1.0 raises `SchemaError` for anything but `True` or `False`.
- **Schema nodes are validated when built**: `String` checks that the codec exists and is a
  text codec (`"hex"`, `"base64"` or `"zlib"` are refused),
  `Array` checks its element and dimension count (1 to 64), and `Cluster` requires unique `str` names
  and real schema nodes. Each raises `SchemaError`. Duplicate field names used to be
  accepted and silently lost data on unpack.
- **Ragged arrays are refused.** `pack(Array(I32, 2), [[1, 2], [3]])` used to write bytes
  LabVIEW could not read back; it now raises `SchemaError`.
- **No stray standard-library exceptions.** Out-of-range floats, EXT values and time stamp
  seconds, unencodable text, undecodable text, unknown encodings and over-deep nesting used
  to leak `OverflowError`, `struct.error`, `UnicodeError`, `LookupError` or
  `RecursionError`; they now raise `SchemaError` or `DataError`. Decoding an EXT beyond the
  double range returns infinity instead of raising `OverflowError`, and EXT values in the
  double subnormal range round once, to the nearest double.
- Error messages say "an 8-bit" and "a 16-bit", and "1 trailing byte".
- Scalar nodes repr as their public names (`I32`, `DBL`, `Boolean`, ...), and `Array`,
  `String` and `Cluster` have compact reprs.

### Added

- `Bytes`, a schema node for LabVIEW strings used as byte buffers; its value is `bytes`
  (`bytes` in the text form, a hex string in CLI JSON).
- `Cluster` also accepts a dict of field name to schema.
- `unpack_from(schema, data, offset=0)`, which reads one value from the middle of a buffer
  and returns it with the offset of the next byte, for several flattened values sent back to
  back (the "rest of the flattened string" output of LabVIEW's Unflatten From String).
- `LVTimestamp.from_datetime()` and `LVTimestamp.to_datetime()`; a naive datetime raises
  `SchemaError` and an out-of-range time stamp raises `DataError`.
- `unpack` and `unpack_from` accept any object supporting the buffer protocol (`bytes`,
  `bytearray`, `memoryview`, `array.array`, `mmap`, ...) and raise `TypeError` for anything
  else. `unpack_from` reads it in place and releases it before returning or raising, so a
  caller may grow its `bytearray` inside the `except` block.
- Quoted field names in the schema text form (`cluster("Error Code":i32)`), so any name
  round-trips through `format_schema` and `parse_schema`; nesting beyond 64 levels is refused.
- Decoding untrusted data is bounded: size headers that promise more data than exists fail at
  once, and objects that cost no input bytes (rows of an empty array, dicts of empty
  clusters at any depth) share a budget of 1024 plus one per input byte (`DataError` beyond
  that). For `unpack_from` only the bytes the value itself has read count, so walking a
  stream of hostile records stays linear.
- Schemas and `TrailingDataError` copy and pickle (0.3.0 `Cluster` could not be deep-copied
  or pickled).
- Values that misbehave (a list subclass that lies about its length, a `str` whose `encode`
  returns text, a `float` subclass with a broken `__float__`, a mapping whose `in` lies) raise
  `SchemaError` or pack correctly instead of corrupting output or leaking `TypeError` or
  `KeyError`; `Cluster(5)` raises `SchemaError`; a released `memoryview` raises `TypeError`.
- `DataError` and `TrailingDataError` in the public API.
- A guide (`GUIDE.md`) covering every public name; doctests on every public name.
- Every worked example from NI's "Flattened Data" page, copied as fetched, as test vectors.
- 24 more real LabVIEW 2026 captures (33 in all): EXT values, U64, 1-D and 2-D DBL arrays,
  I32, Boolean and 2-D string arrays, nested clusters, and a time stamp.
- Seeded fuzz and adversarial tests, and a mutation round proving the contract tests catch
  injected bugs.

### Fixed

- The hand-written time stamp vector labelled 2002-01-01 encoded 2001-12-31; it is corrected
  and cross-checked against `datetime`. Vectors that were labelled as NI-documented but were
  hand-derived are now labelled as hand-derived, in the tests and in the capture manifest.

## [0.3.0]

### Fixed

- `BoolArray` now flattens as one byte per element after the I32 count, matching real LabVIEW
  "Flatten To String" output and the NI "Flattened Data" reference. Earlier releases bit-packed
  the elements MSB-first, which did not match LabVIEW. This changes the bytes produced for any
  boolean array, including boolean arrays nested inside clusters.

### Added

- Golden fixtures captured from real LabVIEW 2026 (26.3.1f1) under
  `tests/fixtures/real_labview/`: the DBL values 0.25 and 1.0, NaN, positive and negative
  infinity, boolean TRUE and FALSE, the string "ABC", and the empty string, each with a
  `manifest.json` recording how it was produced and cross-checked.
- A contract test (`tests/test_real_labview.py`) that decodes every real LabVIEW fixture end to
  end and re-flattens it byte-for-byte.
- NI-documented composite vectors (`tests/test_documented_composites.py`) for an I32, a 1-D and
  a 2-D DBL array, a 128-bit timestamp, and a mixed cluster, labeled as documentation-derived
  rather than captured.
- A real end-to-end test (`tests/test_real_cli_e2e.py`) that drives the installed `lvflatten`
  console script over the real fixture bytes through `subprocess`.

## [0.2.0]

### Added

- A compact schema text form with `parse_schema(text)` and `format_schema(schema)`, so a
  schema can be written on one line (for example `cluster(id:i32, name:string, ok:bool)`) and
  rendered back out.
- An `lvflatten` command-line tool (console entry point) with `unflatten` (hex to JSON) and
  `flatten` (JSON to hex) subcommands, a `--little` byte-order flag, a `--no-size` top-level
  prefix toggle, stdin input, and worked examples in `--help`.

## [0.1.0]

### Added

- `pack(schema, value)` and `unpack(schema, data)` for the LabVIEW "Flatten To String" format.
- A typed schema builder: `I8` `I16` `I32` `I64` `U8` `U16` `U32` `U64`, `SGL`, `DBL`, `EXT`,
  `Boolean`, `BoolArray`, `String`, `Array`, `Cluster` and `Timestamp` (with the `LVTimestamp`
  value type).
- Big-endian by default with a `byte_order` option, and a `prepend_size` toggle for the
  top-level I32 size prefix on strings and arrays.
- `LVFlattenError` and the `SchemaError` and `TruncatedDataError` it covers.
