#!/usr/bin/env python3
"""Contract test for the generated debug index.

Two checks:

  1. the committed annex is fresh, so a module that gains a switch, a state
     dump or a force hook without a regenerated annex fails the gate; and
  2. every addon directory has a row in the annex, or is on the exemption
     allowlist, so a parser regression that drops a module fails the gate.

Run: python3 -m unittest tools.tests.test_debug_index -v
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.validation import gen_debug_index as gen  # noqa: E402


class TestDebugIndexFresh(unittest.TestCase):
    """The committed annex matches the sources."""

    def test_check_exits_zero(self) -> None:
        result = subprocess.run(
            [sys.executable, "tools/validation/gen_debug_index.py", "--check"],
            cwd=REPO,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"annex is stale:\n{result.stdout}\n{result.stderr}",
        )


class TestDebugIndexCoverage(unittest.TestCase):
    """Every addon has a row or is on the exemption allowlist."""

    def test_every_addon_is_covered(self) -> None:
        rows = {module.name for module in gen.collect_modules()}
        exempt = set(gen.EXEMPTIONS)
        uncovered = sorted(set(gen.all_addons()) - rows - exempt)
        self.assertEqual(
            uncovered, [], f"addons with no row and no exemption: {uncovered}"
        )

    def test_no_addon_is_both_row_and_exempt(self) -> None:
        rows = {module.name for module in gen.collect_modules()}
        both = sorted(rows & set(gen.EXEMPTIONS))
        self.assertEqual(both, [], f"addons with both a row and an exemption: {both}")


if __name__ == "__main__":
    unittest.main()
