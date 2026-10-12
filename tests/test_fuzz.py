"""Seeded property and fuzz tests: random schemas, random values, random and mutated bytes.

Every run uses fixed seeds, so a failure reproduces exactly. The properties: a value packs
and unpacks back to itself in both byte orders; a schema survives the text form; and no
input, however malformed, makes the codec raise anything but its own documented errors.
"""

from __future__ import annotations

import contextlib
import random
import string

import pytest

from lvflatten import (
    DBL,
    EXT,
    I8,
    I16,
    I32,
    I64,
    SGL,
    U8,
    U16,
    U32,
    U64,
    Array,
    Boolean,
    Bytes,
    Cluster,
    LVFlattenError,
    LVTimestamp,
    Schema,
    SchemaError,
    String,
    Timestamp,
    format_schema,
    pack,
    parse_schema,
    unpack,
)

_LEAVES: list[Schema] = [I8, I16, I32, I64, U8, U16, U32, U64, SGL, DBL, EXT, Boolean]
_LEAVES += [Timestamp, Bytes, String(), String("latin-1")]
_INT_RANGES: dict[Schema, tuple[int, int]] = {
    node: ((-(1 << (bits - 1)), (1 << (bits - 1)) - 1) if signed else (0, (1 << bits) - 1))
    for node, bits, signed in [
        (I8, 8, True),
        (I16, 16, True),
        (I32, 32, True),
        (I64, 64, True),
        (U8, 8, False),
        (U16, 16, False),
        (U32, 32, False),
        (U64, 64, False),
    ]
}
_NAME_CHARS = string.ascii_letters + string.digits + ' _-."\\:(),'


def _schema(rng: random.Random, depth: int = 0) -> Schema:
    roll = rng.random()
    if depth >= 3 or roll < 0.5:
        return rng.choice(_LEAVES)
    if roll < 0.75:
        return Array(_schema(rng, depth + 1), rng.choice([1, 1, 2, 3]))
    names = {"".join(rng.choices(_NAME_CHARS, k=rng.randint(0, 6))) for _ in range(4)}
    return Cluster([(name, _schema(rng, depth + 1)) for name in sorted(names)])


def _value(rng: random.Random, schema: Schema) -> object:
    if schema in _INT_RANGES:
        low, high = _INT_RANGES[schema]
        return rng.choice([low, high, 0, rng.randint(low, high)])
    if schema in (SGL, DBL):
        number = rng.uniform(-1e6, 1e6)
        if schema == DBL:
            return number
        single = unpack(SGL, pack(SGL, number))  # snap to the nearest single
        assert isinstance(single, float)
        return single
    if schema == EXT:
        return rng.choice([0.0, -0.0, 1.5, rng.uniform(-1e300, 1e300), 5e-324])
    if schema == Boolean:
        return rng.random() < 0.5
    if schema == Timestamp:
        return LVTimestamp(rng.randint(-(1 << 63), (1 << 63) - 1), rng.randint(0, (1 << 64) - 1))
    if schema == Bytes:
        return rng.randbytes(rng.randint(0, 8))
    if isinstance(schema, String):
        alphabet = string.printable + ("éü" if schema.encoding == "latin-1" else "中")
        return "".join(rng.choices(alphabet, k=rng.randint(0, 8)))
    if isinstance(schema, Array):
        return _rows(rng, schema, [rng.randint(0, 3) for _ in range(schema.ndims)])
    assert isinstance(schema, Cluster)
    return {name: _value(rng, sub) for name, sub in schema.fields}


def _rows(rng: random.Random, schema: Array, dims: list[int]) -> list[object]:
    if len(dims) == 1:
        return [_value(rng, schema.element) for _ in range(dims[0])]
    return [_rows(rng, schema, dims[1:]) for _ in range(dims[0])]


@pytest.mark.parametrize("seed", range(40))
def test_random_values_round_trip_in_both_byte_orders(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(25):
        schema = _schema(rng)
        value = _value(rng, schema)
        for order in ("big", "little"):
            blob = pack(schema, value, byte_order=order)
            assert unpack(schema, blob, byte_order=order) == value
            assert pack(schema, unpack(schema, blob, byte_order=order), byte_order=order) == blob


@pytest.mark.parametrize("seed", range(40))
def test_random_schemas_survive_the_text_form(seed: int) -> None:
    rng = random.Random(1000 + seed)
    for _ in range(25):
        schema = _schema(rng)
        assert parse_schema(format_schema(schema)) == schema


@pytest.mark.parametrize("seed", range(30))
def test_random_bytes_only_raise_documented_errors(seed: int) -> None:
    rng = random.Random(2000 + seed)
    for _ in range(40):
        schema = _schema(rng)
        data = rng.randbytes(rng.randint(0, 64))
        for order in ("big", "little"):
            with contextlib.suppress(LVFlattenError):
                unpack(schema, data, byte_order=order)


@pytest.mark.parametrize("seed", range(30))
def test_mutated_valid_blobs_only_raise_documented_errors(seed: int) -> None:
    rng = random.Random(3000 + seed)
    for _ in range(25):
        schema = _schema(rng)
        blob = bytearray(pack(schema, _value(rng, schema)))
        for _ in range(6):
            mutant = bytearray(blob)
            action = rng.randrange(4)
            if action == 0 and mutant:
                mutant[rng.randrange(len(mutant))] = rng.randrange(256)
            elif action == 1:
                del mutant[rng.randrange(len(mutant) + 1) :]
            elif action == 2:
                mutant += rng.randbytes(rng.randint(1, 5))
            elif mutant:
                at = rng.randrange(len(mutant))
                mutant[at : at + 4] = b"\x7f\xff\xff\xff"
            with contextlib.suppress(LVFlattenError):
                unpack(schema, bytes(mutant))


@pytest.mark.parametrize("seed", range(30))
def test_random_schema_text_only_raises_schema_error(seed: int) -> None:
    rng = random.Random(4000 + seed)
    pieces = ["array", "cluster", "string", "i32", "dbl", "(", ")", ",", ":", '"', "\\", "2", "x"]
    for _ in range(60):
        text = " ".join(rng.choices(pieces, k=rng.randint(0, 12)))
        if rng.random() < 0.3:
            text += "".join(rng.choices(string.printable, k=5))
        with contextlib.suppress(SchemaError):
            parse_schema(text)
