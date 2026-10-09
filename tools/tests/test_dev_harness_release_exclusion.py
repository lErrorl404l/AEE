#!/usr/bin/env python3
"""The dev harness cannot ship in a release artefact.

Two proofs.

Part (a), STATIC reference assertion (runs in --fast): no file under
``addons/`` or ``optionals/`` references ``dev-harness``, ``aee_dev_`` or
``[AEE][dev]``.  The dev harness is a standalone HEMTT project under
``tools/dev-harness/``, outside the addon tree, so no shipped addon may
reach it.

Part (b), RELEASE-TREE assertion (runs in the full sweep only): the tree
named by the environment variable ``AEE_RELEASE_TREE`` carries no
``aee_dev.pbo`` and no dev ``.so``/``.dll`` anywhere, including the mod
root.  The phase gate runs ``hemtt release`` first and sets
``AEE_RELEASE_TREE``.  A missing or stale tree SKIPS with a recorded reason
for a local run, and FAILS when ``AEE_REQUIRE_RELEASE_TREE=1`` is set, so a
skip can never hide a broken gate in CI.

Run: python3 -m unittest tools.tests.test_dev_harness_release_exclusion
"""

from __future__ import annotations

import os
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADDON_ROOTS = (REPO / "addons", REPO / "optionals")

# A reference that ties a shipped addon to the dev harness.
FORBIDDEN = ("dev-harness", "aee_dev_", "[AEE][dev]")

# The dev PBO HEMTT names for the standalone project (prefix aee + addon dev),
# and the plain name a hand-rolled build could produce.  Either is a leak.
DEV_PBO_NAMES = {"aee_dev.pbo", "dev.pbo"}

# Source files that can carry a textual reference.  A binary asset (a .paa, a
# .p3d, an engine PBO) cannot hold one, so it is not read.
TEXT_SUFFIXES = {
    ".sqf",
    ".sqs",
    ".hpp",
    ".h",
    ".cpp",
    ".inc",
    ".txt",
    ".md",
    ".xml",
    ".json",
    ".csv",
    ".cfg",
    ".ext",
    ".toml",
    ".yml",
    ".yaml",
}


def _is_text_file(path: Path) -> bool:
    if path.name.startswith("$"):
        return True
    return path.suffix.lower() in TEXT_SUFFIXES


def _text_files(root: Path):
    if not root.is_dir():
        return
    for path in root.rglob("*"):
        if path.is_file() and _is_text_file(path):
            yield path


def _newest_mtime(root: Path) -> float:
    newest = 0.0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        newest = max(newest, mtime)
    return newest


def _newest_source_mtime() -> float:
    newest = 0.0
    for root in ADDON_ROOTS:
        newest = max(newest, _newest_mtime(root))
    project = REPO / ".hemtt" / "project.toml"
    if project.is_file():
        newest = max(newest, project.stat().st_mtime)
    return newest


def _is_dev_artefact(path: Path) -> bool:
    name = path.name.lower()
    if name in DEV_PBO_NAMES:
        return True
    if name.endswith((".so", ".dll", ".pbo")) and "aee_dev" in name:
        return True
    return name.startswith("libaee_dev") and name.endswith(".so")


class TestStaticReferences(unittest.TestCase):
    """Part (a): no shipped addon may name the dev harness."""

    def test_no_shipped_addon_references_the_dev_harness(self):
        hits = []
        for root in ADDON_ROOTS:
            for path in _text_files(root):
                text = path.read_text(encoding="utf-8", errors="replace")
                for token in FORBIDDEN:
                    if token in text:
                        hits.append(f"{path.relative_to(REPO)}: {token}")
        self.assertEqual(
            hits,
            [],
            "shipped addon files reference the dev harness:\n" + "\n".join(hits),
        )


class TestReleaseTree(unittest.TestCase):
    """Part (b): the release tree carries no dev artefact."""

    def _skip_or_fail(self, reason: str, require: bool) -> None:
        if require:
            self.fail(reason)
        self.skipTest(reason)

    def test_release_tree_carries_no_dev_artefact(self):
        tree = os.environ.get("AEE_RELEASE_TREE", "").strip()
        require = os.environ.get("AEE_REQUIRE_RELEASE_TREE") == "1"

        if not tree:
            self._skip_or_fail(
                "AEE_RELEASE_TREE is unset; run `hemtt release` and set it",
                require,
            )
        root = Path(tree)
        if not root.is_dir():
            self._skip_or_fail(
                f"AEE_RELEASE_TREE does not name a directory: {tree}",
                require,
            )

        if _newest_mtime(root) <= _newest_source_mtime():
            self._skip_or_fail(
                "release tree is older than the newest source; run "
                "`hemtt release` first",
                require,
            )

        hits = []
        for path in root.rglob("*"):
            if path.is_file() and _is_dev_artefact(path):
                hits.append(str(path.relative_to(root)))
        self.assertEqual(
            hits,
            [],
            "release tree carries a dev artefact:\n" + "\n".join(sorted(hits)),
        )


if __name__ == "__main__":
    unittest.main()
