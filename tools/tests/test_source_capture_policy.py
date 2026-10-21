#!/usr/bin/env python3
"""The capture policy: a sources directory tracks JSON only.

The repository publishes the extracted data and its citations. It never
publishes the captured third-party pages, drawings or manuals, because they
belong to their publishers. The bytes are held in the local cache that
``tools/validation/source_cache.py`` names, outside the working tree.

This test fails, naming the path, when any tracked file under
``data/*/sources/`` is not a JSON record. There is no allowlist: the policy
is JSON only.
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def tracked_sources_files() -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "-z", "--", "data/*/sources/*"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [name for name in result.stdout.split("\0") if name]


class TestSourceCapturePolicy(unittest.TestCase):
    def setUp(self) -> None:
        self.files = tracked_sources_files()
        if not self.files:
            self.skipTest("not a git checkout, or no tracked sources files")

    def test_only_json_is_tracked_under_sources(self):
        offenders = [
            name for name in self.files if Path(name).suffix.lower() != ".json"
        ]
        self.assertEqual(
            offenders,
            [],
            "a captured page, drawing or manual is tracked in the repository; "
            "the bytes belong in the local source cache "
            f"(tools/validation/source_cache.py): {offenders}",
        )

    def test_the_json_records_remain(self):
        self.assertTrue(
            [name for name in self.files if name.endswith(".json")],
            "every sources directory lost its JSON records",
        )


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False).result.wasSuccessful() else 1)
