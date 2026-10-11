# lvflatten round 2: real LabVIEW fixtures and documented composites

Round 1 shipped the full codec (0.2.0) with golden vectors hand-derived from NI's "Flattened
Data" reference. Round 2 raises the bar of trust: it brings in bytes captured from a real
LabVIEW 2026 install and, in doing so, exposes and fixes a genuine codec bug.

## What the real fixtures let us certify

Nine byte sequences were captured on LabVIEW 2026 (26.3.1f1) by driving shipped VIs through the
ActiveX / VI Server COM interface and reading the raw `data string` indicator. They are stored
under `tests/fixtures/real_labview/` with a `manifest.json` that records the capture method and
cross-checks. They let us certify, against the real tool rather than against documentation:

- DBL encoding is big-endian IEEE 754: 0.25 is `3fd0000000000000`, 1.0 is `3ff0000000000000`.
- Special doubles round-trip exactly as LabVIEW emits them: NaN is the quiet pattern
  `7ff8000000000000`, +Inf is `7ff0000000000000`, -Inf is `fff0000000000000`. Python's own
  `struct` produces the identical bytes, so `pack` and `unpack` are byte-exact here.
- Boolean is a single byte: TRUE is `01`, FALSE is `00`.
- String is an I32 big-endian length prefix then the bytes: "ABC" is `00000003414243`, the
  empty string is `00000000`. This confirms the prepend-size default is ON and big-endian.

The contract test `tests/test_real_labview.py` decodes every fixture, checks the value, and
re-flattens it byte-for-byte. `tests/test_real_cli_e2e.py` drives the installed `lvflatten`
console script over the same bytes through `subprocess`.

## The gap the real-vs-documented split exposes

LabVIEW VI Scripting is not reachable over the ActiveX / VI Server COM interface on this
machine: the type library has no Diagram / Node / Constant classes, and COM can only run
existing VIs and get or set their controls, not build a diagram. No shipped, runnable VI exposes
a settable control of the composite types (I32 scalar, arrays, timestamp, cluster) wired to
Flatten To String. So those shapes could not be captured and their expected bytes come from NI
documentation instead.

This is handled by keeping the two sources strictly apart and labeling them honestly:

- `tests/test_real_labview.py` and `tests/fixtures/real_labview/` hold only LabVIEW-captured
  bytes.
- `tests/test_documented_composites.py` holds the NI-documented composites (I32 -19, 1-D and
  2-D DBL arrays, the 2002 timestamp, and the mixed cluster) and says in its own module
  docstring that they are documentation-derived, not captured.
- The README gained a "Golden fixtures and provenance" section drawing the same line.

## The codec fix the documented bytes reveal

The NI-documented cluster vector ends its boolean array `[F, T, T, F]` as `00000004 00 01 01 00`:
an I32 count then one byte per element. The 0.2.0 codec instead bit-packed boolean arrays
MSB-first (`[T, F, T]` became `00000003 a0`). That never matched LabVIEW; it only matched the
library's own hand-derived vector from round 1, which carried the same mistake.

Round 2 fixes `pack_bool_array` / `unpack_bool_array` to emit and read one byte per element,
updates the `BoolArrayType` docstring, the README table, and every affected vector
(`test_bool.py`, `test_claims.py`, `test_cli_e2e.py`). This is the one behavioral change in the
release, so the version bumps to 0.3.0 and the changelog calls it out under Fixed. Scalars,
floats, strings, arrays of other types, clusters and timestamps are unchanged.

## Remaining API / CLI polish considered

- The CLI and public API are unchanged and still pass their round-1 contracts; no new surface
  was needed to consume the fixtures, which is the right outcome for an additive round.
- JSON output of NaN and Infinity relies on Python's `json` extension tokens (`NaN`,
  `Infinity`); the real-e2e test asserts they round-trip through the installed script, so the
  behavior is now pinned rather than assumed.
- `_parse.py` remains the longest module at 205 lines; it predates this round and was left
  untouched to keep the change additive. Splitting the tokenizer from the parser is a candidate
  for a later, non-fixture round.

## Out of scope for round 2

Variant, waveform, path, refnum, enum and fixed-point types, Flatten To JSON / XML token
capture, and type-descriptor driven schema inference all remain future work; the manifest lists
them among the cases that COM could not capture.
