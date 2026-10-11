#!/usr/bin/env python3
"""The addon inventory in the docs must match the tree under ``addons/``.

Discovery is by reading the tree and the documents, never by memory, so a
stale count, a renamed addon or a dead section heading fails the gate.

Three guarantees:

(a) ``README.md`` states the real addon total and names every addon.
(b) ``docs/wiki/chapters/introduction.qmd`` states the same total and names
    the same addons.
(c) Every ``## `` section heading in ``docs/wiki/chapters/modules.qmd``,
    other than ``Compat addons``, names a directory that exists under
    ``addons/``.

Run: python3 -m unittest tools.tests.test_docs_addon_index
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADDONS = REPO / "addons"
README = REPO / "README.md"
INTRO = REPO / "docs" / "wiki" / "chapters" / "introduction.qmd"
MODULES = REPO / "docs" / "wiki" / "chapters" / "modules.qmd"

# A section heading in the module reference.
_HEADING = re.compile(r"^## (.+)$", re.MULTILINE)


def _inventory() -> tuple[list[str], list[str]]:
    """Return ``(core, compat)`` addon names read from the tree."""
    names = sorted(p.parent.name for p in ADDONS.glob("*/config.cpp"))
    core = [n for n in names if not n.startswith("compat_")]
    compat = [n for n in names if n.startswith("compat_")]
    return core, compat


class TestAddonInventory(unittest.TestCase):
    def setUp(self) -> None:
        self.core, self.compat = _inventory()
        self.total = len(self.core) + len(self.compat)
        self.every = self.core + self.compat

    def test_readme_states_the_total(self) -> None:
        text = README.read_text(encoding="utf-8")
        self.assertIn(
            f"{self.total} addons under `addons/`",
            text,
            f"README.md must state '{self.total} addons under `addons/`'",
        )

    def test_readme_names_every_addon(self) -> None:
        text = README.read_text(encoding="utf-8")
        missing = [n for n in self.every if f"`{n}`" not in text]
        self.assertEqual(
            missing,
            [],
            "addons not named in README.md: " + ", ".join(missing),
        )

    def test_introduction_states_the_total_and_names_every_addon(self) -> None:
        text = INTRO.read_text(encoding="utf-8")
        self.assertIn(
            f"{self.total} addons under `addons/`",
            text,
            f"introduction.qmd must state '{self.total} addons under `addons/`'",
        )
        missing = [n for n in self.every if f"`{n}`" not in text]
        self.assertEqual(
            missing,
            [],
            "addons not named in introduction.qmd: " + ", ".join(missing),
        )

    def test_module_headings_are_real_addons(self) -> None:
        text = MODULES.read_text(encoding="utf-8")
        bad = []
        for raw in _HEADING.findall(text):
            name = raw.strip()
            if name == "Compat addons":
                continue
            if not (ADDONS / name).is_dir():
                bad.append(name)
        self.assertEqual(
            bad,
            [],
            "modules.qmd headings that are not addons: " + ", ".join(bad),
        )


if __name__ == "__main__":
    unittest.main()
