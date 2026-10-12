# lvflatten 1.0.0 certification report

Progress:
- [x] Branch `release/1.0.0` created from `main` (0.3.0)
- [x] Baseline gates run on 0.3.0
- [x] API review and 1.0.0 API changes (item 1)
- [x] Errors, typing, docstrings and doctests (items 2 to 5)
- [x] Ground truth: NI reference re-fetched, 33 real LabVIEW captures (item 7)
- [x] Contract, fuzz and mutation round (items 6, 9, 18)
- [x] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [x] Packaging, e2e and upgrade from PyPI 0.3.0 (items 8, 10, 13, 14)
- [x] Version bump to 1.0.0
- [x] Independent reviewer and five QA lenses report PASS (items 16, 19)
- [x] Gates (item 15)
- [ ] PR and trace guard (item 17)

## Baseline on 0.3.0 (before any change)

| Command | Result |
| --- | --- |
| `ruff format --check .`, `ruff check .`, `mypy --strict src tests` | exit 0 |
| `pytest` | 234 passed |
| `pytest --doctest-modules src` | no doctests at all |

Defects found in 0.3.0 during this round: EXT used the x87 80-bit layout while LabVIEW writes
IEEE binary128; vectors labelled "NI-documented" were not on NI's page and one of them (the
"2002-01-01" time stamp) encoded 2001-12-31; ragged arrays packed silently into unreadable
bytes; duplicate cluster names lost data; `OverflowError`, `struct.error`, `UnicodeError`,
`LookupError` and `RecursionError` leaked from `pack`, `unpack` and `parse_schema`; a few
bytes could ask `unpack` for billions of empty lists; `prepend_size=False` was ignored for
`BoolArray`.

## Scorecard (author)

| # | Item | Verdict | Evidence |
| --- | --- | --- | --- |
| 1 | API reviewed for stability | PASS | Changes listed in CHANGELOG 1.0.0 with migration notes: `DataError`/`TrailingDataError`, errors also `ValueError`, `BoolArray == Array(Boolean)`, `Schema` base class, `Literal` byte order, validated nodes, `Bytes`, dict clusters, `LVTimestamp` datetime helpers, quoted names, EXT binary128 |
| 2 | `__all__` exact, no private imports in docs | PASS | `tests/test_contract.py::test_all_lists_exactly_the_public_api`; `tests/test_docs.py::test_examples_import_only_public_names` |
| 3 | Docstring with runnable example on every public name, doctests pass | PASS | `tests/test_docs.py` (every module doctested, every `__all__` name has `>>>` and appears in an example); 0 failures |
| 4 | Typed end to end | PASS | `mypy --strict src tests` exit 0; `py.typed` in wheel; public returns are `bytes`, `object` (documented), `Schema`, `str`; `data` is a `Buffer` that an external `mypy --strict` consumer can pass `array.array`, `mmap` or ctypes to; `typing.get_type_hints` resolves on every public function on 3.10 and 3.14 |
| 5 | Typed, documented, safe errors | PASS | `tests/test_errors.py` (hierarchy, every leak path, messages under 120 chars for 100 kB input, packed values never echoed); GUIDE section 4 |
| 6 | Contract asserts the full promise | PASS | 918 tests; every public name covered by contract files (`test_contract`, `test_schema_nodes`, `test_errors`, `test_bytes_and_time`, `test_options`, `test_parse`, `test_cli*`) |
| 7 | Real ground truth | PASS | 33 captures from LabVIEW 2026 26.3.1f1 on this PC with manifest (`tests/test_real_labview.py`); every worked example of NI "Flattened Data" fetched 2026-10-12 (URL in `tests/test_ni_reference.py`); hand-derived vectors labelled and cross-checked with `struct`/`datetime`; EXT cross-checked against an exact-`Fraction` oracle on 2000 random doubles |
| 8 | Real e2e incl. PyPI upgrade | PASS | lens (d) at e9d24dd: wheel in unactivated venvs on 3.10 to 3.14 with a global editable install first on PATH, consumer script and CLI by subprocess, suite from the extracted sdist with `src` removed (871 passed each), sdist install; a deliberately broken installed CLI makes 37 of 38 CLI tests fail, proving they drive the build under test; PyPI 0.3.0 upgraded in place to the 1.0.0 wheel, every behaviour change matches CHANGELOG 1.0.0 |
| 9 | Seeded fuzz, no crash, hang or blow-up | PASS | `tests/test_fuzz.py` (round trips both byte orders, text form, random and mutated bytes, random schema text), `tests/test_adversarial.py` (lying sizes fail fast, amplification refused, deep nesting, linear growth) |
| 10 | Every interpreter on this PC | PASS | 871 passed against the installed wheel on 3.10.19, 3.11.5, 3.12.12, 3.13.2, 3.14.2 (lens d, e9d24dd); none missing from `requires-python` up |
| 11 | README | PASS | `twine check --strict` PASSED; absolute links enforced by `tests/test_docs.py`; problem, why (PyPI facts checked 2026-10-12), install, quick start, GUIDE and CHANGELOG links |
| 12 | CHANGELOG dated 1.0.0 | PASS | `## [1.0.0] - 2026-10-12` with stable surface summary |
| 13 | pyproject | PASS | 1.0.0, Production/Stable, 3.10 to 3.14 classifiers, MIT, Homepage/Source/Issues/Changelog, keywords, `dependencies = []` (contract-tested) |
| 14 | sdist and wheel contents | PASS | wheel: 20 modules + `py.typed` + LICENSE; sdist: src, tests, fixtures, README, GUIDE, CHANGELOG, LICENSE, pyproject, plus the `.gitignore` hatchling always adds (accepted); no process notes; embedded data is LabVIEW output captured by the author and short quoted NI examples with source URL |
| 15 | Gates exit 0 alone | PASS | `ruff format --check .` 0, `ruff check .` 0, `mypy --strict src` 0, `pytest` 0 (918 passed), each run alone |
| 16 | Independent reviewer | PASS | items 1 to 18 all PASS on re-review (see below) |
| 17 | PR, trace guard | pending | see below |
| 18 | Mutation round | PASS | author round: 26 mutations, 1 survivor fixed; blind lens (e) rounds: see below, every survivor got a contract and was re-killed |
| 19 | Five QA lenses | PASS | a, b, c, d, e all PASS after their findings were fixed and re-verified (see below) |

## Mutation round (item 18)

Each mutation was applied alone to the source, the full suite run with `-x`, and the source
restored. "Caught by" is the first failing test.

| Mutation | File | Result | Caught by |
| --- | --- | --- | --- |
| signed and unsigned integer formats swapped | `_numeric.py` | killed | `test_claims::test_golden_bytes_decode_to_the_value[i8_negative]` |
| little-endian maps to big-endian | `_codec.py` | killed | `test_cli::test_little_endian_and_no_size` |
| string length prefix off by one | `_string.py` | killed | `test_adversarial::test_decoding_time_grows_linearly` |
| array dimensions read in reverse order | `_array.py` | killed | `test_adversarial::test_output_blow_up_is_refused_quickly[empty_rows_2d]` |
| only byte 01 decodes as TRUE | `_numeric.py` | killed | doctest of `_schema` |
| EXT exponent bias off by one | `_ext.py` | killed | `test_claims::...[ext_one]` |
| EXT NaN payload dropped | `_ext.py` | killed | `test_ext::test_nan_keeps_its_sign_and_quiet_bit` |
| EXT x87 explicit integer bit | `_ext.py` | killed | `test_claims::test_value_encodes_to_the_golden_bytes[ext_one]` |
| time stamp seconds read unsigned | `_timestamp.py` | killed | `test_bytes_and_time::test_dates_before_1904_are_negative_seconds` |
| trailing bytes accepted | `_codec.py` | killed | doctest of `_errors` |
| `TrailingDataError` not a `DataError` | `_errors.py` | killed | GUIDE example |
| no budget for zero-cost objects | `_reader.py` | killed | `test_adversarial::...[empty_cluster_elements]` |
| `prepend_size=False` strips one dimension only | `_codec.py` | survived, then killed | new `test_options::test_prepend_size_false_drops_every_dimension_of_a_2d_array` |
| cluster fields packed in reverse order | `_cluster.py` | killed | `test_bytes_and_time::test_bytes_inside_a_cluster` |
| spaces allowed in bare names | `_parse.py` | killed | doctest of `_format` |
| undecodable text replaced, not refused | `_string.py` | killed | `test_cli::test_bad_input_exits_one_with_a_message` |
| duplicate cluster names accepted | `_compound.py` | killed | `test_schema_nodes::test_cluster_rejects_bad_fields[duplicate]` |
| ragged arrays accepted | `_array.py` | killed | `test_errors::test_wrong_values_raise_schema_error` |
| `to_datetime` truncates instead of rounding | `_lvtime.py` | killed | `test_bytes_and_time::test_microseconds_survive_a_round_trip` |
| non-bytes data not refused with `TypeError` | `_codec.py` | killed | `test_errors::test_non_bytes_data_is_a_type_error` |
| `bool` accepted as an integer | `_numeric.py` | killed | `test_errors::test_wrong_values_raise_schema_error` |
| negative string length accepted | `_string.py` | killed | doctest of `_errors` |
| SGL packed as DBL | `_numeric.py` | killed | `test_claims::...[sgl_one]` |
| `Bytes` as a list in CLI JSON | `_json.py` | killed | `test_cli::test_bytes_travel_as_hex_in_json` |
| text nesting limit off | `_parse.py` | killed | `test_adversarial::test_text_nesting_limit` |
| `format_schema` drops the dimension count | `_format.py` | killed | doctest of `_format` |

## Ground truth details (item 7)

- `tests/fixtures/real_labview/`: 33 files from LabVIEW 2026 26.3.1f1. 13 are the output of
  shipped VIs that wrap Flatten To String; 20 are fields of LabVIEW front-panel datalog
  records, whose encoding was checked against Flatten To String output in the same run
  (DBL 0.25 and string "ABC" byte-identical). NI's page states that extended numbers are
  flattened in the same 128-bit form LabVIEW saves to disk.
- Not capturable on this PC: `I8`, `I16`, `U16`, `SGL` and `I64` scalars (no shipped VI with
  such a control that runs headless), a time stamp with a nonzero fraction, little-endian
  output, and EXT through the Flatten To String primitive itself. These are covered by NI's
  rules, hand-derived vectors and the `struct` oracle.

## Blind mutation rounds by QA lens (e) (items 18 and 19e)

Each round was designed without seeing the author's table or the previous round's fixes,
applied one mutation at a time to a fresh clone, and run against the full suite with `-x`.
Every survivor that changed observable behaviour got a contract test, and the next round
first re-applied it to confirm the kill.

| Round | Mutations | Killed | Equivalent | Survived, then contract added | New contracts |
| --- | --- | --- | --- | --- | --- |
| 1 | 49 | 42 | 0 | 7 | `tests/test_qa_contracts.py` |
| 2 | 23 | 16 | 1 | 6 | `tests/test_qa_boundaries.py` |
| 3 | 16 | 10 | 2 | 4 | `tests/test_qa_round3.py` |
| 4 | 18 | 8 | 0 | 10 | `tests/test_qa_round4.py` |
| 5 | 23 | 18 | 0 | 5 | `tests/test_qa_round5.py`, budget probes and a per-test deadline |
| 6 | 23 | 13 | 0 | 10 | `tests/test_qa_round6.py` |
| 7 | 25 | 15 | 2 | 8 | `tests/test_qa_round7.py` |
| 8 | 26 | 15 | 4 | 7 | `tests/test_qa_round8.py` |
| 9 | 25 | 13 | 2 | 10 | `tests/test_qa_round9.py`, a live decoder check in `String` |
| 10 | 19 | 10 | 6 | 3 | `tests/test_qa_round10.py` |
| final | re-check | all 70 survivors re-applied across the rounds are killed | | 0 | |
| total | 247 | 160 | 17 | 70, all closed | |

Equivalent mutations, with the reason each cannot change behaviour: the I32 format `i` read
as `l` (struct with an explicit byte order always uses standard sizes); `LookupError` dropped
from the CLI handler (every lookup path is already converted to `SchemaError`); the explicit
`str` guard in the buffer adapter (`memoryview(str)` raises the same `TypeError`); the EXT
NaN test written as `exponent == ALL_ONES and fraction` (the other branch also yields an
infinity with the right sign); the array shape read from the last row instead of the first
(only the wording of an error on input that is both ragged and too shallow changes); the
string length written as unsigned (lengths are capped at 2**31 - 1 first); the empty-row
count without its early exit (it only adds zeros); the input view not released explicitly
in `unpack` (it is local and freed on return); the time stamp branch of the CLI JSON
conversion (JSON already writes the named tuple as a two-item list); the reader's end
test written as `==` (the position can never pass the end). One mutation exposed dead code:
`b"".decode(encoding)` never calls the codec for empty input, so the decoder check in
`String` now goes through `codecs.lookup(encoding).decode(b"")`. Round 10 equivalents:
an EXT scale test at exactly zero (both paths round once to the same double); a hidden bit
on binary128 subnormals (all far below the double range, both give a signed zero); a
redundant `bytes()` on data the reader already returns as bytes; a stream flag on the
no-size reader (only arrays use it and that path reads fixed-size elements); the parser's
program name (only the private `python -m lvflatten._cli` spelling would change).

Notable gaps the rounds closed: little-endian time stamp layout had no golden vector; a
value read with `unpack_from` at an offset could borrow the bytes before it for its decode
budget; `--little` and `--no-size` were untested on the CLI `flatten` side; bytes and time stamps inside clusters and N-D arrays in CLI JSON; dates before 1904
with a fraction; error message bounds. A broken decode budget used to hang the suite; the
blow-up tests now run a bounded probe first and `tests/conftest.py` sets a per-test
deadline, so such a regression fails in seconds.

## Independent reviews (items 16 and 19)

Every reviewer was independent of the author, followed the factory rules and CERT-1.0.md,
worked in its own clone, ran things rather than reading, and reported back privately.

| Lens | First verdict | Findings | Final verdict |
| --- | --- | --- | --- |
| Item 16 reviewer | FAIL (item 8) | CLI e2e tests ran whatever `lvflatten` was first on PATH and could `pip install -e .` | PASS on re-review: items 1 to 18 all PASS; the sabotaged venv CLI makes 37 of 38 CLI tests fail |
| a. API and docs | FAIL (1 medium, 5 low) | "any bytes-like object" not delivered; BoolArray unpack migration note; a node class passed as a schema; NumPy scalars; encoding spelling changed equality; stable attributes undocumented. Then `data` type hint too narrow (medium) and `get_type_hints` failing at runtime (low) | PASS at e6a9438: all fixed, 13 doc examples and 3 CLI transcripts run, doctests pass, external `mypy --strict` consumer clean |
| b. Correctness and ground truth | PASS (3 low) | capture manifest kept old "NI-documented" labels and the wrong 2002 value; two test docstrings overstated provenance; little-endian Timestamp and EXT layouts undocumented | PASS at 1a9e032: NI page re-fetched, 33/33 captures and 9/9 NI examples decoded by an independent `struct`/`Fraction` oracle, 6000 random schemas, 80000 EXT patterns and 40000 time stamp cases with 0 failures |
| c. Adversarial and robustness | FAIL (1 high, 2 medium, 5 low) | `unpack_from` loops could build millions of objects from a few bytes; a `bytearray` stayed locked inside `except`; huge `ndims` in schema text; `TrailingDataError` pickling; quadratic walk over strided views; other buffers refused; a lying `__len__` | PASS at a2e8e87 (fresh reviewer): all fixed; 3.55M fuzz cases, 1.53M schema texts and 190 CLI runs with no leak, hang or superlinear growth; accepted: CLI traceback on a broken stdout pipe (standard Python behaviour), schema-factor memory with many dimensions (documented) |
| d. Packaging and real e2e | FAIL (1 medium, 2 low) | the CLI e2e defect above; `.gitignore` in the sdist (hatchling always adds it, accepted); one CHANGELOG line | PASS at e9d24dd: 871 passed on 3.10 to 3.14 from the installed wheel, sdist install, PyPI 0.3.0 upgrade path matches CHANGELOG |
| e. Contract strength | FAIL (7 survivors) | ten blind rounds, see the table above | PASS at aa16e0d: every non-equivalent mutation killed; the reviewer judged the unmutated surface exhausted (constants pinned indirectly, docstrings, help text) |

Decisions taken on reviewer questions: `pack` has no free-object budget, so a value with
more than about a thousand empty rows or empty clusters packs but `unpack` refuses it; this
is documented in GUIDE section 4 and pinned by a contract, as the price of a hard bound on
what hostile bytes can cost.
