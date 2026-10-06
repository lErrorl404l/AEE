#!/usr/bin/env python3
"""The test runner must bound every external command with a timeout.

A hung suite must fail fast and report, not block the sweep forever.
"""

import importlib.util
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "aee_run_tests", ROOT / "tools" / "run_tests.py"
)
run_tests = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(run_tests)


class TestCommandTimeout(unittest.TestCase):
    def test_an_overrunning_command_is_killed_and_reported(self):
        original = run_tests.CMD_TIMEOUT_S
        run_tests.CMD_TIMEOUT_S = 1.0
        try:
            start = time.monotonic()
            rc = run_tests.run(f'{sys.executable} -c "import time; time.sleep(30)"')
            elapsed = time.monotonic() - start
        finally:
            run_tests.CMD_TIMEOUT_S = original
        self.assertEqual(rc, 124)
        self.assertLess(elapsed, 5.0, f"took {elapsed:.2f}s")

    def test_a_fast_command_still_returns_its_code(self):
        rc = run_tests.run(f'{sys.executable} -c "raise SystemExit(0)"')
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
