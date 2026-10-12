import importlib.resources

import lvflatten

# The public API. This list is the contract; the tests below fail the moment the module and
# this list disagree.
PUBLIC_API: list[str] = [
    "DBL",
    "EXT",
    "I16",
    "I32",
    "I64",
    "I8",
    "SGL",
    "U16",
    "U32",
    "U64",
    "U8",
    "Array",
    "BoolArray",
    "Boolean",
    "Bytes",
    "Cluster",
    "DataError",
    "LVFlattenError",
    "LVTimestamp",
    "Schema",
    "SchemaError",
    "String",
    "Timestamp",
    "TrailingDataError",
    "TruncatedDataError",
    "format_schema",
    "pack",
    "parse_schema",
    "unpack",
]


def test_all_lists_exactly_the_public_api() -> None:
    assert sorted(lvflatten.__all__) == sorted(PUBLIC_API)


def test_every_exported_name_resolves() -> None:
    for name in lvflatten.__all__:
        assert hasattr(lvflatten, name)


def test_version_is_a_three_part_string() -> None:
    parts = lvflatten.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


def test_the_package_ships_type_information() -> None:
    assert importlib.resources.files("lvflatten").joinpath("py.typed").is_file()
