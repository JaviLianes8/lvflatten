import pytest

from lvflatten import (
    DBL,
    EXT,
    I16,
    I32,
    U8,
    Array,
    BoolArray,
    Boolean,
    Cluster,
    SchemaError,
    String,
    Timestamp,
    format_schema,
    parse_schema,
)


def test_parse_scalar_is_case_insensitive() -> None:
    assert parse_schema("I32") is I32
    assert parse_schema("dbl") is DBL
    assert parse_schema("ext") is EXT
    assert parse_schema("bool") is Boolean
    assert parse_schema("boolarray") is BoolArray
    assert parse_schema("timestamp") is Timestamp


def test_parse_string_with_and_without_encoding() -> None:
    assert parse_schema("string") == String()
    assert parse_schema("string(latin-1)") == String("latin-1")


def test_parse_array_dimensions() -> None:
    assert parse_schema("array(dbl)") == Array(DBL)
    assert parse_schema("array(i16, 2)") == Array(I16, 2)


def test_parse_nested_cluster() -> None:
    schema = parse_schema("cluster(id:i32, point:cluster(x:dbl, y:dbl), tags:array(string))")
    assert schema == Cluster(
        [
            ("id", I32),
            ("point", Cluster([("x", DBL), ("y", DBL)])),
            ("tags", Array(String())),
        ]
    )


def test_parse_empty_cluster() -> None:
    assert parse_schema("cluster()") == Cluster([])


def test_whitespace_is_ignored() -> None:
    assert parse_schema("  array(  u8 , 3 )  ") == Array(U8, 3)


def test_format_round_trips_every_shape() -> None:
    schema = Cluster(
        [
            ("n", I32),
            ("name", String("latin-1")),
            ("grid", Array(DBL, 2)),
            ("flags", BoolArray),
            ("when", Timestamp),
        ]
    )
    assert parse_schema(format_schema(schema)) == schema


def test_format_uses_the_plain_names() -> None:
    assert format_schema(Array(DBL)) == "array(dbl)"
    assert format_schema(String()) == "string"
    assert format_schema(Cluster([("a", U8)])) == "cluster(a:u8)"


def test_unknown_type_raises() -> None:
    with pytest.raises(SchemaError):
        parse_schema("i33")


def test_trailing_tokens_raise() -> None:
    with pytest.raises(SchemaError):
        parse_schema("i32 dbl")


def test_unbalanced_parentheses_raise() -> None:
    with pytest.raises(SchemaError):
        parse_schema("array(i32")


def test_bad_character_raises() -> None:
    with pytest.raises(SchemaError):
        parse_schema("array(i32)!")


def test_non_integer_dimension_raises() -> None:
    with pytest.raises(SchemaError):
        parse_schema("array(i32, two)")
