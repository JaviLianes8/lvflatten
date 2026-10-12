"""Contracts added after the independent 1.0 reviews: each pins a promise a reviewer found loose."""

from __future__ import annotations

import random
from fractions import Fraction

import pytest

import lvflatten
from lvflatten import (
    EXT,
    I8,
    I16,
    I32,
    I64,
    Array,
    Cluster,
    DataError,
    Schema,
    SchemaError,
    String,
    TrailingDataError,
    TruncatedDataError,
    pack,
    parse_schema,
    unpack,
    unpack_from,
)


def _binary128_value(word: int) -> Fraction:
    exponent = (word >> 112) & 0x7FFF
    fraction = word & ((1 << 112) - 1)
    if exponent == 0:
        return Fraction(fraction, 1 << (16382 + 112))
    return Fraction((1 << 112) | fraction) * Fraction(2) ** (exponent - 16383 - 112)


def test_ext_decoding_rounds_once_even_into_double_subnormals() -> None:
    rng = random.Random(1022)
    for _ in range(4000):
        exponent = rng.randint(16383 - 1080, 16383 - 1015)  # around the double subnormal range
        word = (exponent << 112) | rng.getrandbits(112)
        decoded = unpack(EXT, word.to_bytes(16, "big"))
        assert decoded == float(_binary128_value(word))


def test_reviewer_ext_example_decodes_to_the_nearest_double() -> None:
    word = 0x3BFFFC8C0BB45C645800000000000000
    assert unpack(EXT, word.to_bytes(16, "big")) == float(_binary128_value(word))


@pytest.mark.parametrize("codec", ["hex", "rot13", "base64", "zlib", "bz2"])
def test_non_text_codecs_are_refused_when_the_node_is_built(codec: str) -> None:
    with pytest.raises(SchemaError):
        String(codec)
    with pytest.raises(SchemaError):
        parse_schema(f"string({codec})")


def test_cluster_values_may_carry_extra_keys() -> None:
    schema = Cluster({"a": I32})
    assert pack(schema, {"a": 1, "unused": "x"}) == pack(schema, {"a": 1})


@pytest.mark.parametrize("flag", [0, 1, "no", None])
def test_prepend_size_must_be_a_bool(flag: object) -> None:
    with pytest.raises(SchemaError):
        pack(String(), "a", prepend_size=flag)  # type: ignore[arg-type]
    with pytest.raises(SchemaError):
        unpack(String(), b"a", prepend_size=flag)  # type: ignore[arg-type]


def test_the_schema_base_class_cannot_be_built_directly() -> None:
    with pytest.raises(TypeError):
        Schema()


def test_the_package_namespace_exposes_only_public_names() -> None:
    public = {name for name in dir(lvflatten) if not name.startswith("_")}
    assert public == set(lvflatten.__all__)


def _count(n: int) -> bytes:
    return n.to_bytes(4, "big")


def test_free_object_budget_is_a_floor_plus_one_per_input_byte() -> None:
    # 65536 free objects plus one per input byte: four header bytes allow 65540 empty clusters.
    assert len(unpack(Array(Cluster([])), _count(65540))) == 65540  # type: ignore[arg-type]
    with pytest.raises(DataError):
        unpack(Array(Cluster([])), _count(65541))
    # Eight header bytes allow 65544 empty rows.
    assert len(unpack(Array(I8, 2), _count(65544) + _count(0))) == 65544  # type: ignore[arg-type]
    with pytest.raises(DataError):
        unpack(Array(I8, 2), _count(65545) + _count(0))


def test_nested_empty_clusters_are_charged_per_dict() -> None:
    two_dicts = Cluster([("x", Cluster([]))])
    assert len(unpack(Array(two_dicts), _count(32770))) == 32770  # type: ignore[arg-type]
    with pytest.raises(DataError):
        unpack(Array(two_dicts), _count(32771))


def test_what_pack_writes_unpack_reads_for_small_empty_shapes() -> None:
    for schema, value in [
        (Array(Cluster([])), [{}] * 5),
        (Array(Cluster([]), 2), [[{}] * 3] * 3),
        (Array(I8, 3), [[[]] * 4] * 4),
    ]:
        assert unpack(schema, pack(schema, value)) == value


def test_error_wording() -> None:
    with pytest.raises(SchemaError, match="for an 8-bit signed integer"):
        pack(I8, 999)
    with pytest.raises(SchemaError, match="for a 16-bit signed integer"):
        pack(I16, 1 << 20)
    with pytest.raises(SchemaError, match="for a 64-bit signed integer"):
        pack(I64, 1 << 70)
    with pytest.raises(TrailingDataError, match=r"^1 trailing byte left"):
        unpack(I8, b"\x00\x00")


def test_unpack_from_walks_back_to_back_values() -> None:
    record = Cluster([("n", I16), ("s", String())])
    stream = pack(record, {"n": 1, "s": "a"}) + pack(record, {"n": 2, "s": "bc"})
    first, offset = unpack_from(record, stream)
    second, end = unpack_from(record, stream, offset)
    assert (first, second) == ({"n": 1, "s": "a"}, {"n": 2, "s": "bc"})
    assert (offset, end) == (7, len(stream))


def test_unpack_from_little_endian_and_bytes_like() -> None:
    assert unpack_from(I16, bytearray(b"\x01\x00\xff"), byte_order="little") == (1, 2)
    assert unpack_from(I16, memoryview(b"\xff\x00\x01"), 1) == (1, 3)


@pytest.mark.parametrize("offset", [-1, 4, 1.0, True, "0"])
def test_unpack_from_rejects_bad_offsets(offset: object) -> None:
    with pytest.raises(SchemaError):
        unpack_from(I16, b"\x00\x01\x02", offset)  # type: ignore[arg-type]


def test_unpack_from_errors_match_unpack() -> None:
    with pytest.raises(TruncatedDataError):
        unpack_from(I32, b"\x00\x00\x00\x00\x01", 3)
    with pytest.raises(TypeError):
        unpack_from(I32, "0000")  # type: ignore[arg-type]
    with pytest.raises(DataError):
        unpack_from(Array(Cluster([])), b"\xff\xff" + _count(65541), 2)
    assert unpack_from(Cluster([]), b"\x00" * 4, 4) == ({}, 4)  # offset may equal the length
