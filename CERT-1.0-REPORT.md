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
- [ ] Independent reviewer and five QA lenses report PASS (items 16, 19)
- [ ] Gates (item 15), PR and trace guard (item 17)

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
| 4 | Typed end to end | PASS | `mypy --strict src tests` exit 0 (43 files); `py.typed` in wheel; public returns are `bytes`, `object` (documented), `Schema`, `str` |
| 5 | Typed, documented, safe errors | PASS | `tests/test_errors.py` (hierarchy, every leak path, messages under 120 chars for 100 kB input, packed values never echoed); GUIDE section 4 |
| 6 | Contract asserts the full promise | PASS | 708 tests; every public name covered by contract files (`test_contract`, `test_schema_nodes`, `test_errors`, `test_bytes_and_time`, `test_options`, `test_parse`, `test_cli*`) |
| 7 | Real ground truth | PASS | 33 captures from LabVIEW 2026 26.3.1f1 on this PC with manifest (`tests/test_real_labview.py`); every worked example of NI "Flattened Data" fetched 2026-10-12 (URL in `tests/test_ni_reference.py`); hand-derived vectors labelled and cross-checked with `struct`/`datetime`; EXT cross-checked against an exact-`Fraction` oracle on 2000 random doubles |
| 8 | Real e2e incl. PyPI upgrade | PASS | wheel and sdist into clean venvs, external consumer + CLI by subprocess (`consumer OK` on 3.10 to 3.14 and from sdist); PyPI 0.3.0 installed, 0.3-era code run, upgraded to 1.0.0 wheel, same code passes; changed behaviours observed exactly as the CHANGELOG states (EXT bytes, `array(bool)`, `DataError`) |
| 9 | Seeded fuzz, no crash, hang or blow-up | PASS | `tests/test_fuzz.py` (round trips both byte orders, text form, random and mutated bytes, random schema text), `tests/test_adversarial.py` (lying sizes fail fast, amplification refused, deep nesting, linear growth) |
| 10 | Every interpreter on this PC | PASS | 708 passed against the installed wheel on 3.10.19, 3.11.5, 3.12.12, 3.13.2, 3.14.2; none missing from `requires-python` up |
| 11 | README | PASS | `twine check --strict` PASSED; absolute links enforced by `tests/test_docs.py`; problem, why (PyPI facts checked 2026-10-12), install, quick start, GUIDE and CHANGELOG links |
| 12 | CHANGELOG dated 1.0.0 | PASS | `## [1.0.0] - 2026-10-12` with stable surface summary |
| 13 | pyproject | PASS | 1.0.0, Production/Stable, 3.10 to 3.14 classifiers, MIT, Homepage/Source/Issues/Changelog, keywords, `dependencies = []` (contract-tested) |
| 14 | sdist and wheel contents | PASS | wheel: package + `py.typed` + LICENSE; sdist: src, tests, fixtures, README, GUIDE, CHANGELOG, LICENSE, pyproject (process notes excluded); embedded data is LabVIEW output captured by the author and short quoted NI examples with source URL |
| 15 | Gates exit 0 alone | PASS | `ruff format --check .` 0, `ruff check .` 0, `mypy --strict src` 0, `pytest` 0 (708 passed) |
| 16 | Independent reviewer | pending | see below |
| 17 | PR, trace guard | pending | see below |
| 18 | Mutation round | PASS | 26 mutations, 25 killed at once, 1 survivor fixed with a new contract and re-killed (table below) |
| 19 | Five QA lenses | pending | see below |

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

## Independent reviews (items 16 and 19)

Pending.
