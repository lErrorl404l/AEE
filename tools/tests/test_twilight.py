#!/usr/bin/env python3
"""Twilight illuminance: the generated kernel reproduces the held table.

Run: python3 -m unittest tools.tests.test_twilight
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from sqf_lite import run_sqf  # noqa: E402
from tools import gen_twilight as gen  # noqa: E402

KERNEL = REPO / "addons/core/functions/fnc_twilightIlluminance.sqf"


class TestTwilight(unittest.TestCase):
    def test_fresh(self):
        self.assertEqual(gen.main(["--check"]), 0)

    def test_every_row_reproduced_in_float32(self):
        rows = json.loads(gen.DATA.read_text(encoding="utf-8"))["rows"]
        self.assertEqual(len(rows), 37)
        for r in rows:
            got = run_sqf(KERNEL, [r["altitude"]], {}, float32=True)
            self.assertAlmostEqual(got / 10 ** r["log10_lux"], 1.0, delta=1e-4, msg=r)

    def test_published_anchors(self):
        for alt, lux in ((0, 759), (-6, 3.41), (-12, 0.00806), (-18, 0.000645)):
            self.assertAlmostEqual(run_sqf(KERNEL, [alt]) / lux, 1.0, delta=0.03)

    def test_outside_twilight_is_zero(self):
        self.assertEqual(run_sqf(KERNEL, [5]), 0)
        self.assertEqual(run_sqf(KERNEL, [-20]), 0)


if __name__ == "__main__":
    unittest.main()
