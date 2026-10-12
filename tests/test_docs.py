"""The documentation is executable: doctests, README and GUIDE examples all run and pass."""

from __future__ import annotations

import doctest
import importlib
import pkgutil
import re
from pathlib import Path

import pytest

import lvflatten

_ROOT = Path(__file__).resolve().parent.parent
_MODULES = ["lvflatten"] + [f"lvflatten.{m.name}" for m in pkgutil.iter_modules(lvflatten.__path__)]
_BLOCK = re.compile(r"```python\n(.*?)```", re.DOTALL)


@pytest.mark.parametrize("name", _MODULES)
def test_module_doctests_pass(name: str) -> None:
    result = doctest.testmod(importlib.import_module(name), optionflags=doctest.ELLIPSIS)
    assert result.failed == 0


@pytest.mark.parametrize("name", lvflatten.__all__)
def test_every_public_name_has_a_docstring_with_an_example(name: str) -> None:
    doc = getattr(lvflatten, name).__doc__ or ""
    assert ">>>" in doc, name


def test_the_doctests_cover_every_public_name() -> None:
    finder = doctest.DocTestFinder()
    examples = "".join(
        example.source
        for module in _MODULES
        for test in finder.find(importlib.import_module(module))
        for example in test.examples
    )
    for name in lvflatten.__all__:
        assert re.search(rf"\b{name}\b", examples), name


@pytest.mark.parametrize("document", ["README.md", "GUIDE.md"])
def test_document_examples_run(document: str) -> None:
    text = (_ROOT / document).read_text(encoding="utf-8")
    blocks = _BLOCK.findall(text)
    assert blocks, document
    for block in blocks:
        exec(compile(block, document, "exec"), {})


@pytest.mark.parametrize("document", ["README.md", "GUIDE.md", "CHANGELOG.md"])
def test_documents_use_absolute_links(document: str) -> None:
    text = (_ROOT / document).read_text(encoding="utf-8")
    for target in re.findall(r"\]\(([^)]+)\)", text):
        assert target.startswith(("https://", "#")), f"{document}: {target}"


def test_examples_import_only_public_names() -> None:
    for document in ("README.md", "GUIDE.md"):
        text = (_ROOT / document).read_text(encoding="utf-8")
        assert not re.search(r"lvflatten\._[a-z]", text), document
