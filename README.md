# lvflatten

Read and write LabVIEW "Flatten To String" data from Python, with no LabVIEW installed.

## The problem

LabVIEW's Flatten To String turns any wire (a number, a string, an array, a cluster) into a
compact binary string, and that string is the usual shape of data that leaves LabVIEW over
TCP, UDP, a serial line or a file. The bytes carry no type information: NI's reference says
so in as many words, and LabVIEW's own Unflatten From String needs the type wired in. A
Python program on the other end therefore has to know the type up front and decode the
layout by hand, one `struct.unpack` at a time.

`lvflatten` does that decoding and encoding for you. You declare the LabVIEW type once as a
schema, and the library packs Python values into the exact bytes LabVIEW produces or unpacks
LabVIEW's bytes into plain Python values.

## Install

```
pip install lvflatten
```

Pure standard library, no runtime dependencies, Python 3.10 or newer, fully typed.

## Quick start

```python
from lvflatten import DBL, I32, Array, Boolean, Cluster, String, pack, unpack

# A cluster, as LabVIEW would send it over TCP.
reading = Cluster([("id", I32), ("label", String()), ("samples", Array(DBL)), ("ok", Boolean)])

blob = pack(reading, {"id": 7, "label": "probe", "samples": [0.25, 1.0], "ok": True})
assert blob.hex() == ("000000070000000570726f6265000000023fd00000000000003ff000000000000001")
assert unpack(reading, blob) == {"id": 7, "label": "probe", "samples": [0.25, 1.0], "ok": True}
```

The same schema can be written as text, which is handy in configuration files and on the
command line:

```python
from lvflatten import parse_schema

schema = parse_schema('cluster(id:i32, label:string, samples:array(dbl), "Error Code":i32)')
```

```
$ lvflatten unflatten -s "cluster(id:i32, name:string, ok:bool)" -x 000000070000000570726f626501
{
  "id": 7,
  "name": "probe",
  "ok": true
}
$ lvflatten flatten -s "array(dbl)" -j "[1.0, 2.0]"
000000023ff00000000000004000000000000000
```

Every type, option, error and the command-line tool are covered in the
[guide](https://github.com/JaviLianes8/lvflatten/blob/main/GUIDE.md).

## Supported types

| Schema | LabVIEW type | Flattened form |
| --- | --- | --- |
| `I8 I16 I32 I64 U8 U16 U32 U64` | integers | fixed width, two's complement |
| `SGL` / `DBL` | single / double float | IEEE 754, 4 / 8 bytes |
| `EXT` | extended float | IEEE 754 binary128, 16 bytes |
| `Boolean` | Boolean | one byte, `01` TRUE, `00` FALSE |
| `String(encoding="utf-8")` | string | I32 byte count, then the bytes |
| `Bytes` | string used as a byte buffer | I32 byte count, then the bytes |
| `Array(element, ndims=1)` | array, any dimension | one I32 size per dimension, then the elements |
| `BoolArray` | Boolean array | the same as `Array(Boolean)` |
| `Cluster([(name, schema), ...])` | cluster | the fields back to back, no padding |
| `Timestamp` | 128-bit time stamp | I64 seconds and U64 fraction since 1904 |

Big-endian is the default, as in LabVIEW; `byte_order="little"` and LabVIEW's "prepend array
or string size?" switch (`prepend_size=False`) are both supported.

## Why lvflatten

The format is documented by NI
([Flattened Data](https://www.ni.com/docs/en-US/bundle/labview/page/flattened-data.html)),
but the LabVIEW-related packages on PyPI solve other problems, and none of them is a general
codec for flattened data: [npTDMS](https://pypi.org/project/npTDMS/) and
[nitdms](https://pypi.org/project/nitdms/) read TDMS files,
[pylavi](https://pypi.org/project/pylavi/), [pylabview](https://pypi.org/project/pylabview/)
and [lvkit](https://pypi.org/project/lvkit/) parse VI and other LabVIEW source files, and
[PyVISA](https://pypi.org/project/PyVISA/) and [nidaqmx](https://pypi.org/project/nidaqmx/)
talk to instruments and DAQ hardware. Inside LabVIEW, Flatten To String and Unflatten From
String do this natively, but they are of no use to a Python process. The recurring forum
question ([an NI forum thread on unflattening a LabVIEW TCP string in Python](https://forums.ni.com/t5/LabVIEW/Python-client-to-unflatten-received-string-from-TCP-Labview/m-p/3353607))
is answered with hand-written `struct` code; `lvflatten` replaces that with a declared schema
and an exact, tested round trip.

## Ground truth

The test suite is pinned to three kinds of reference bytes, kept apart so the source of every
expectation is clear:

- **Captured from real LabVIEW 2026** (26.3.1f1, on Windows): 33 byte sequences covering
  every supported type except the `I8`, `I16`, `U16`, `SGL` and `I64` scalars (the 32-bit
  integer was flattened from a U32 control, whose bytes are those of an I32), taken by
  driving shipped VIs
  through LabVIEW's ActiveX interface, either from the output of Flatten To String itself or
  from LabVIEW's front-panel datalog records (whose encoding was checked against Flatten To
  String in the same run):
  [`tests/fixtures/real_labview`](https://github.com/JaviLianes8/lvflatten/tree/main/tests/fixtures/real_labview),
  with a manifest that records how each file was produced.
- **Copied from NI's Flattened Data page**, every worked example on it except the path
  example (paths are out of scope), as fetched on
  2026-10-12, with the page's own sentence next to each vector.
- **Hand-derived** from the documented rules and cross-checked against independent maths
  (`struct` for IEEE 754, `datetime` for the 1904 epoch), and labelled as such.

On top of that come seeded fuzz tests, adversarial-input tests, and a mutation round showing
the contract tests fail for every deliberate bug injected into the codec.

## Scope

Supported: the types in the table above, nested within the documented limits (64 levels in
the text form), in both byte orders, one value per buffer (`unpack`) or several back to back
(`unpack_from`).
Not supported (yet): variants, waveforms, paths, refnums, enums, fixed-point numbers, sets,
maps, LabVIEW classes, and reading LabVIEW type descriptors to build a schema automatically.
`EXT` encodes every Python `float` exactly; decoding rounds LabVIEW's 113-bit significand to
the nearest double.

## More

- [Guide](https://github.com/JaviLianes8/lvflatten/blob/main/GUIDE.md): every type, option,
  error and the command-line tool.
- [Changelog](https://github.com/JaviLianes8/lvflatten/blob/main/CHANGELOG.md), including
  the migration notes from 0.x to 1.0.
- License: [MIT](https://github.com/JaviLianes8/lvflatten/blob/main/LICENSE).
- Author: Javier Lianes ([lianes8studio.com](https://lianes8studio.com),
  [GitHub](https://github.com/JaviLianes8),
  [LinkedIn](https://www.linkedin.com/in/jlianes/)).
