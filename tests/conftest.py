"""Suite-wide guard: a test that runs away (for example a broken decode budget building
billions of objects) aborts the run with a traceback instead of hanging the machine."""

from __future__ import annotations

import faulthandler
from collections.abc import Iterator

import pytest

_DEADLINE_SECONDS = 60


@pytest.fixture(autouse=True)
def _deadline() -> Iterator[None]:
    faulthandler.dump_traceback_later(_DEADLINE_SECONDS, exit=True)
    try:
        yield
    finally:
        faulthandler.cancel_dump_traceback_later()
