#!/usr/bin/env python3
"""Guard for tools/validation/validate_cba_settings.py.

The validator cross-references the CBA settings and the aee_ namespace: a dead
setting, a stale test read, a wrong prefix or an undocumented write is a wiring
defect.  This runs the validator and fails on a non-zero exit, so a regression
cannot pass CI, and it pins the bare-global scanner that the optics registries
need.

Run: python3 -m unittest tools.tests.test_cba_settings -v
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))


class TestCbaSettingsValidator(unittest.TestCase):
    def test_validator_is_green(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(REPO / "tools" / "validation" / "validate_cba_settings.py"),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_scanner_sees_a_bare_global_assignment(self):
        from tools.validation import validate_cba_settings as v

        self.assertTrue(
            v._DIRECT_ASSIGN.search("aee_cartography_terrainTables = call (compile ...)")
        )
        self.assertFalse(v._DIRECT_ASSIGN.search("aee_x == other"))
        self.assertFalse(v._DIRECT_ASSIGN.search("local_x = 1"))


if __name__ == "__main__":
    unittest.main()
