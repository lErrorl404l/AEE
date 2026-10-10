#!/usr/bin/env python3
"""Freshness, completeness and grounding gate for ``docs/icd/``.

Three guarantees:

(a) The committed ICD set is fresh: it matches the generator
    ``tools/architecture/interface_contracts.py`` output.
(b) The README index names every ``*.md`` in the directory, and every
    document the index names exists. Discovery is by reading the README and
    by globbing the directory, never by memory.
(c) Every variable an ICD names is a real cross-addon read in the source.
    An invented variable fails the gate. This is the wiring check of issue
    #73 step 3.

The gate also fails on a local path leak, so an ICD names a file and a
line, never a path on one machine.

Run: python3 -m unittest tools.tests.test_icd_docs
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.architecture import interface_contracts as gen  # noqa: E402

ICD = REPO / "docs" / "icd"
README = ICD / "README.md"

_LINK = re.compile(r"\]\(([^)\s]+)\)")
_VARIABLE = re.compile(r"`(aee_[A-Za-z0-9_]+)`")

LEAKS: dict[str, re.Pattern[str]] = {
    "temporary path": re.compile(r"/tmp"),
    "machine install path": re.compile(r"/ext/"),
    "Windows drive path": re.compile(r"[A-Za-z]:\\"),
}


def _index_links() -> list[str]:
    targets = []
    for raw in _LINK.findall(README.read_text(encoding="utf-8")):
        target = raw.split("#", 1)[0]
        if not target or "://" in target:
            continue
        if target.startswith("/") or target.startswith("../"):
            continue
        targets.append(target)
    return targets


class TestFreshness(unittest.TestCase):
    def test_the_committed_set_is_fresh(self) -> None:
        self.assertEqual(gen.check(), 0)

    def test_the_cli_check_passes(self) -> None:
        self.assertEqual(gen.main(["--check"]), 0)


class TestIndex(unittest.TestCase):
    def test_readme_exists(self) -> None:
        self.assertTrue(README.is_file(), f"{README} is missing")

    def test_every_indexed_document_exists(self) -> None:
        for target in _index_links():
            with self.subTest(target=target):
                self.assertTrue(
                    (ICD / target).is_file(),
                    f"README names {target}, which does not exist",
                )

    def test_every_document_is_indexed(self) -> None:
        indexed = set(_index_links())
        on_disk = {p.name for p in ICD.glob("*.md") if p.name != README.name}
        missing = sorted(on_disk - indexed)
        self.assertEqual(
            missing,
            [],
            "documents not named in the README index: " + ", ".join(missing),
        )


class TestGrounding(unittest.TestCase):
    def test_every_named_variable_is_a_real_cross_addon_read(self) -> None:
        real = set()
        for variables in gen.scan().values():
            real.update(variables)
        invented = []
        for path in sorted(ICD.glob("*.md")):
            if path.name == README.name:
                continue
            for variable in set(_VARIABLE.findall(path.read_text(encoding="utf-8"))):
                if variable not in real:
                    invented.append(f"{path.name}: {variable}")
        self.assertEqual(
            invented,
            [],
            "ICD variables that are not cross-addon reads:\n" + "\n".join(invented),
        )


class TestPortable(unittest.TestCase):
    def test_no_absolute_local_path_leaks(self) -> None:
        hits = []
        for path in sorted(ICD.rglob("*")):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for label, pattern in LEAKS.items():
                for match in pattern.finditer(text):
                    line = text.count("\n", 0, match.start()) + 1
                    hits.append(f"{path.relative_to(REPO)}:{line}: {label}")
        self.assertEqual(
            hits,
            [],
            "absolute local paths in docs/icd/:\n" + "\n".join(hits),
        )


if __name__ == "__main__":
    unittest.main()
