#!/usr/bin/env python3
"""The engine reference under ``docs/engine/`` must be self-consistent and
portable.

Two guarantees:

(a) Every document the README index names exists, and every ``*.md`` in the
    directory is named by the index. Discovery is by reading the README and
    by globbing the directory, never by memory, so a named-but-missing or a
    written-but-unlisted document fails.
(b) No absolute local path leaks into ``docs/engine/``: no temporary path, no
    machine install path, no Windows drive path. The reference names a PBO and
    a line, never a path on one machine.

Run: python3 -m unittest tools.tests.test_engine_docs
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ENGINE = REPO / "docs" / "engine"
README = ENGINE / "README.md"

# A markdown link target: [text](target).
_LINK = re.compile(r"\]\(([^)\s]+)\)")

# Leak pattern -> what it is. A path that names one machine must not ship.
LEAKS: dict[str, re.Pattern[str]] = {
    "temporary path": re.compile(r"/tmp"),
    "machine install path": re.compile(r"/ext/"),
    "Windows drive path": re.compile(r"[A-Za-z]:\\"),
}


def _index_links() -> list[str]:
    """Local document targets named by the README index."""
    targets = []
    for raw in _LINK.findall(README.read_text(encoding="utf-8")):
        target = raw.split("#", 1)[0]
        if not target or "://" in target:
            continue
        if target.startswith("/") or target.startswith("../"):
            continue
        targets.append(target)
    return targets


class TestIndex(unittest.TestCase):
    def test_readme_exists(self) -> None:
        self.assertTrue(README.is_file(), f"{README} is missing")

    def test_every_indexed_document_exists(self) -> None:
        for target in _index_links():
            with self.subTest(target=target):
                self.assertTrue(
                    (ENGINE / target).is_file(),
                    f"README names {target}, which does not exist",
                )

    def test_every_document_is_indexed(self) -> None:
        indexed = set(_index_links())
        on_disk = {p.name for p in ENGINE.glob("*.md") if p.name != README.name}
        missing = sorted(on_disk - indexed)
        self.assertEqual(
            missing,
            [],
            "documents not named in the README index: " + ", ".join(missing),
        )


class TestPortable(unittest.TestCase):
    def test_no_absolute_local_path_leaks(self) -> None:
        hits = []
        for path in sorted(ENGINE.rglob("*")):
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
            "absolute local paths in docs/engine/:\n" + "\n".join(hits),
        )


if __name__ == "__main__":
    unittest.main()
