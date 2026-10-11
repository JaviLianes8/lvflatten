# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
