# lvflatten

Schema-driven codec for LabVIEW's "Flatten To String" binary format.

## Install

```
pip install lvflatten
```

## Usage

Flattened LabVIEW data carries no type information, so the caller declares the type with a
schema and the library packs or unpacks the bytes against it.

```python
from lvflatten import I32, DBL, Array, Cluster, String, Boolean, pack, unpack

# A scalar.
data = pack(I32, 42)            # b"\x00\x00\x00\x2a"  (big-endian)
assert unpack(I32, data) == 42

# A string: an I32 byte count then the bytes.
assert pack(String(), "NI") == b"\x00\x00\x00\x02NI"

# An array: an I32 size then the elements.
assert unpack(Array(DBL), pack(Array(DBL), [1.0, 2.0])) == [1.0, 2.0]

# A cluster: ordered named fields, flattened back to back with no padding.
sensor = Cluster([("id", I32), ("label", String()), ("ok", Boolean)])
blob = pack(sensor, {"id": 7, "label": "probe", "ok": True})
assert unpack(sensor, blob) == {"id": 7, "label": "probe", "ok": True}
```

Options on both `pack` and `unpack`:

- `byte_order="big"` (the LabVIEW default) or `"little"`.
- `prepend_size=True` (default). Set it to `False` to drop the leading I32 length of a
  top-level string, or the leading dimension sizes of a top-level array, matching LabVIEW's
  "prepend array or string size?" terminal. Nested strings and arrays always keep their own
  size prefix so they stay self-describing.

The 128-bit timestamp is carried by a small named tuple:

```python
from lvflatten import Timestamp, LVTimestamp, pack, unpack

# Whole seconds since the 1904 epoch, plus a 2**-64 fraction of a second.
ts = LVTimestamp(seconds=2082844800, fraction=0)  # 1970-01-01T00:00:00Z
assert unpack(Timestamp, pack(Timestamp, ts)) == ts
```

## Supported types

| Schema | LabVIEW type | Flattened form |
| --- | --- | --- |
| `I8 I16 I32 I64 U8 U16 U32 U64` | integers | fixed-width, big-endian |
| `SGL` / `DBL` | single / double float | IEEE 754, 4 / 8 bytes |
| `EXT` | extended float | 80-bit value in 16 big-endian bytes |
| `Boolean` | boolean | one byte, 0 or 1 |
| `BoolArray` | boolean array | I32 count then bits packed MSB-first |
| `String(encoding="utf-8")` | string | I32 byte count then the bytes |
| `Array(element, ndims=1)` | array | one I32 per dimension, then row-major elements |
| `Cluster([(name, schema), ...])` | cluster | ordered fields, no padding |
| `Timestamp` | 128-bit timestamp | I64 seconds + U64 fraction, since 1904 |

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
