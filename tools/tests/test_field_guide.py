#!/usr/bin/env python3
"""The engine field guide under ``docs/wiki/field-guide/`` must be
self-consistent and portable.

Two guarantees:

(a) Every page the index names exists, and every ``features/*.qmd`` on disk
    is named by the index.  Discovery is by reading the index and by
    globbing the tree, never by memory, so a named-but-missing or a
    written-but-unlisted page fails.
(b) No absolute local path leaks into ``docs/wiki/field-guide/``: no
    temporary path, no machine install path, no Windows drive path.  The
    guide names a PBO and a line, never a path on one machine.

Run: python3 -m unittest tools.tests.test_field_guide
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GUIDE = REPO / "docs" / "wiki" / "field-guide"
INDEX = GUIDE / "index.qmd"
FEATURES = GUIDE / "features"

# A markdown link target: [text](target).
_LINK = re.compile(r"\]\(([^)\s]+)\)")

# Leak pattern -> what it is.  A path that names one machine must not ship.
LEAKS: dict[str, re.Pattern[str]] = {
    "temporary path": re.compile(r"/tmp"),
    "machine install path": re.compile(r"/ext/"),
    "Windows drive path": re.compile(r"[A-Za-z]:\\"),
}


def _index_links() -> list[str]:
    """Local page targets named by the field-guide index."""
    targets = []
    for raw in _LINK.findall(INDEX.read_text(encoding="utf-8")):
        target = raw.split("#", 1)[0]
        if not target or "://" in target:
            continue
        if target.startswith("/") or target.startswith("../"):
            continue
        targets.append(target)
    return targets


class TestIndex(unittest.TestCase):
    def test_index_exists(self) -> None:
        self.assertTrue(INDEX.is_file(), f"{INDEX} is missing")

    def test_every_indexed_page_exists(self) -> None:
        for target in _index_links():
            with self.subTest(target=target):
                self.assertTrue(
                    (GUIDE / target).is_file(),
                    f"the index names {target}, which does not exist",
                )

    def test_every_feature_page_is_indexed(self) -> None:
        indexed = set(_index_links())
        on_disk = {f"features/{p.name}" for p in FEATURES.glob("*.qmd")}
        missing = sorted(on_disk - indexed)
        self.assertEqual(
            missing,
            [],
            "feature pages not named in the index: " + ", ".join(missing),
        )


class TestPortable(unittest.TestCase):
    def test_no_absolute_local_path_leaks(self) -> None:
        hits = []
        for path in sorted(GUIDE.rglob("*")):
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
            "absolute local paths in docs/wiki/field-guide/:\n" + "\n".join(hits),
        )


if __name__ == "__main__":
    unittest.main()
