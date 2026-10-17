#!/usr/bin/env python3
"""World Magnetic Model WMM2025 (issue: compass declination realism).

The compass declination is the NOAA/BGS World Magnetic Model, generated
from data/magnetism/WMM2025.COF.  These tests EXECUTE the generated SQF
kernel (tools/tests/sqf_lite.py) on NOAA's official test values, so the
check is the mod's own code against the published model.

Run: python3 -m unittest tools.tests.test_wmm
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools import gen_wmm  # noqa: E402
from tools.tests.sqf_lite import run_sqf  # noqa: E402

KERNEL = REPO / "addons/magnetism/functions/fnc_wmmField.sqf"


class TestWmm(unittest.TestCase):
    def test_generated_kernel_is_fresh_and_passes_noaa(self):
        self.assertEqual(gen_wmm.main(["--check"]), 0)

    def test_every_noaa_test_value(self):
        for line in gen_wmm.TESTS.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            v = [float(x) for x in line.split()]
            got = run_sqf(KERNEL, [v[2], v[3], v[1], v[0]], {})
            self.assertAlmostEqual(got[0], v[4], delta=0.01, msg=f"D at {v[2]},{v[3]}")
            self.assertAlmostEqual(got[1], v[5], delta=0.01, msg=f"I at {v[2]},{v[3]}")
            self.assertAlmostEqual(got[3], v[7], delta=1.0)

    def test_compass_uses_the_model(self):
        src = (REPO / "addons/magnetism/functions/fnc_calculateCompassDeviation.sqf").read_text(encoding="utf-8")
        self.assertIn("call FUNC(wmmField)", src)
        self.assertIn("QGVAR(wmmExtrapolate)", src)
        self.assertIn("worldToMgrs", src)
        self.assertIn("date params", src)
        self.assertIn("atan (_anomalyNT / _horizontalNT)", src)
        self.assertNotIn("private _table = [", src)


if __name__ == "__main__":
    unittest.main()
