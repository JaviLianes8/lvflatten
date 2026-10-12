"""Contracts added after the tenth blind mutation round."""

from __future__ import annotations

import pytest

from lvflatten import I16, SchemaError, String, Timestamp, pack, unpack, unpack_from


def test_time_stamp_range_errors_name_the_part() -> None:
    with pytest.raises(SchemaError, match="seconds"):
        pack(Timestamp, (1 << 63, 0))
    with pytest.raises(SchemaError, match="fraction"):
        pack(Timestamp, (0, 1 << 64))


@pytest.mark.parametrize("order", ["network", "native", "=", "!", "<", ">", "BIG", "Little"])
def test_only_big_and_little_are_byte_orders(order: str) -> None:
    with pytest.raises(SchemaError, match="byte_order"):
        pack(I16, 1, byte_order=order)  # type: ignore[arg-type]
    with pytest.raises(SchemaError, match="byte_order"):
        unpack(I16, bytes(2), byte_order=order)  # type: ignore[arg-type]
    with pytest.raises(SchemaError, match="byte_order"):
        unpack_from(I16, bytes(2), byte_order=order)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "call",
    [
        lambda schema: pack(schema, ""),
        lambda schema: unpack(schema, bytes(4)),
        lambda schema: unpack_from(schema, bytes(4)),
    ],
    ids=["pack", "unpack", "unpack_from"],
)
def test_every_entry_point_checks_the_schema_the_same_way(call: object) -> None:
    with pytest.raises(SchemaError, match="String is a class"):
        call(String)  # type: ignore[operator]
    with pytest.raises(SchemaError, match="expected a schema node, got 5"):
        call(5)  # type: ignore[operator]
