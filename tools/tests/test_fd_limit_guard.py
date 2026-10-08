#!/usr/bin/env python3
"""Unit tests for the HEMTT open-file limit guard.

HEMTT holds about one descriptor per packed file (measured peak 5,660 with
the 5,516-marker optics addon; identical with `--threads 1`).  These tests
pin the guard's threshold logic so a low limit fails loudly instead of dying
with `os error 24` part-way through a build.

Run: python3 -m unittest tools.tests.test_fd_limit_guard -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))

import check_fd_limit as guard  # noqa: E402

# The peak measured on the 5,516-marker tree with `hemtt build`.
MEASURED_PEAK_FDS = 5660
MARKER_COUNT = 5516


class TestThreshold(unittest.TestCase):
    def test_required_is_files_plus_headroom(self):
        self.assertEqual(guard.required_limit(1000), 1000 + guard.HEADROOM)

    def test_required_grows_with_the_file_count(self):
        self.assertLess(guard.required_limit(1000), guard.required_limit(2000))

    def test_required_clears_the_measured_peak(self):
        self.assertGreater(guard.required_limit(MEASURED_PEAK_FDS), MEASURED_PEAK_FDS)

    def test_docker_default_limit_is_rejected(self):
        # Docker's default soft nofile is 2048, far below the requirement.
        self.assertFalse(guard.is_adequate(2048, guard.required_limit(MARKER_COUNT)))

    def test_large_limit_is_accepted(self):
        self.assertTrue(guard.is_adequate(1048576, guard.required_limit(MARKER_COUNT)))


class TestFileCount(unittest.TestCase):
    def test_counts_files_recursively(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.paa").write_bytes(b"")
            (root / "sub").mkdir()
            (root / "sub" / "b.paa").write_bytes(b"")
            self.assertEqual(guard.packed_file_count(root), 2)


class TestRepoRequirement(unittest.TestCase):
    def test_current_tree_demands_more_than_the_measured_peak(self):
        required = guard.required_limit(guard.packed_file_count())
        self.assertGreater(required, MEASURED_PEAK_FDS)


if __name__ == "__main__":
    unittest.main()
