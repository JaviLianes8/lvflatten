# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
