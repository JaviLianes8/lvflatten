# lvflatten 1.0.0 certification report

Progress:
- [x] Branch `release/1.0.0` created from `main` (0.3.0)
- [x] Baseline gates run on 0.3.0
- [ ] API review and 1.0.0 API changes (item 1)
- [ ] Errors, typing, docstrings and doctests (items 2 to 5)
- [ ] Ground truth: NI reference re-fetched, real LabVIEW captures imported (item 7)
- [ ] Contract, fuzz and mutation round (items 6, 9, 18)
- [ ] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [ ] Packaging, e2e and upgrade from PyPI 0.3.0 (items 8, 10, 13, 14)
- [ ] Version bump to 1.0.0
- [ ] Independent reviewer and five QA lenses report PASS (items 16, 19)
- [ ] Gates (item 15), PR and trace guard (item 17)

## Baseline on 0.3.0 (before any change)

| Command | Result |
| --- | --- |
| `ruff format --check .` | exit 0 |
| `ruff check .` | exit 0 |
| `mypy --strict src` | exit 0 |
| `mypy --strict src tests` | exit 0 |
| `pytest` | 234 passed |
| `pytest --doctest-modules src` | no doctests at all (item 3 fails) |

Scorecard and evidence follow once each item is verified.
