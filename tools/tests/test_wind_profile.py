#!/usr/bin/env python3
"""Wind near the ground: the Davenport roughness length, the logarithmic
profile from the 10 m meteorological wind, and the crosswind decomposition.

Run: python3 -m unittest tools.tests.test_wind_profile -v
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

Z0 = REPO / "addons/lib/functions/fnc_roughnessLength.sqf"
LOCAL = REPO / "addons/atmos/functions/wind/fnc_getLocalWind.sqf"
CROSS = REPO / "addons/ballistics/functions/fnc_calculateCrosswindBallistics.sqf"


def z0(surface, water=False, snow=0.0):
    g = {
        "surfaceIsWater": lambda p: water,
        "surfaceType": lambda p: surface,
        "missionNamespace": {"__QEGVAR__core_snowDepth_m": snow},
    }
    return run_sqf(Z0, [[0, 0, 0]], g)


class TestRoughness(unittest.TestCase):
    def test_davenport_classes(self):
        for s, v in (("#GdtGrassGreen", 0.03), ("#GdtForestPine", 1.0), ("#GdtAsphalt", 0.005),
                     ("#GdtDirt", 0.1), ("#GdtRock", 0.25), ("#GdtUnknown", 0.1)):
            self.assertAlmostEqual(z0(s), v, places=6, msg=s)

    def test_sea_and_snow(self):
        self.assertAlmostEqual(z0("#GdtGrassGreen", water=True), 0.0002, places=6)
        self.assertAlmostEqual(z0("#GdtForestPine", snow=0.3), 0.005, places=6)


class TestLogProfile(unittest.TestCase):
    def test_source_applies_the_log_law_from_10_m(self):
        src = LOCAL.read_text(encoding="utf-8")
        self.assertIn("(ln (_zEff / _z0)) / (ln (10 / _z0))", src)
        self.assertIn("EFUNC(lib,roughnessLength)", src)

    def test_the_profile_at_rifle_height_over_grass(self):
        # 1.5 m over grass carries ln(1.5/0.03)/ln(10/0.03) = 67 % of the 10 m wind.
        self.assertAlmostEqual(math.log(1.5 / 0.03) / math.log(10 / 0.03), 0.673, places=3)


class TestCrosswind(unittest.TestCase):
    def test_source_fixes(self):
        src = CROSS.read_text(encoding="utf-8")
        self.assertIn("(_wDir select 0) atan2 (_wDir select 1)", src)
        self.assertIn("-(_windSpd * cos (_windDir - _playerDir))", src)
        self.assertIn("eyePos _unit", src)
        self.assertIn("CBA_fnc_currentUnit", src)


if __name__ == "__main__":
    unittest.main()
