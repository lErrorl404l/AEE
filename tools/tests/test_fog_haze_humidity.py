#!/usr/bin/env python3
"""Humidity, fog and haze from physical relations.

  RH    held vapour pressure, RH = 100 e / e_w(T) (WMO-No. 8 Magnus); the
        kernel SQF is executed (sqf_lite) against the formula.
  fog   liquid water from cooling below the dew point, Kunkel (1984)
        extinction 144.7 LWC^0.88 per km (NOAA UPP CALVIS).
  haze  NOAA UPP clear-air visibility 90 exp(-2.5 q), q = RH/100 - 0.15.

Run: python3 -m unittest tools.tests.test_fog_haze_humidity
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.tests.sqf_lite import run_sqf  # noqa: E402

RH_KERNEL = REPO / "addons/atmos/functions/physics/fnc_calculateRelativeHumidity.sqf"
FOG = (REPO / "addons/atmos/functions/state/fnc_updateFog.sqf").read_text(encoding="utf-8")
HAZE = (REPO / "addons/atmos/functions/physics/fnc_calculateHaze.sqf").read_text(encoding="utf-8")


def ew(t: float) -> float:
    return 6.112 * math.exp(17.62 * t / (243.12 + t))


class TestRelativeHumidity(unittest.TestCase):
    def test_kernel_is_the_vapour_pressure_relation(self):
        for rh, tm, tn in ((60, 15, 25), (80, 10, 4), (50, 20, 20), (95, 12, 8), (40, -10, -20)):
            want = round(max(0, min(100, rh * ew(tm) / ew(tn))))
            self.assertEqual(run_sqf(RH_KERNEL, [rh, tm, tn], float32=True), want)

    def test_afternoon_dries_and_night_saturates(self):
        self.assertLess(run_sqf(RH_KERNEL, [70, 15, 24]), 70)
        self.assertEqual(run_sqf(RH_KERNEL, [85, 12, 6]), 100)


class TestFog(unittest.TestCase):
    def lwc(self, td: float, t: float) -> float:
        tk = t + 273.15
        rho_v = 100 * ew(td) / (461.5 * tk) * 1000
        rho_vs = 100 * ew(t) / (461.5 * tk) * 1000
        return min(0.5, max(0.0, rho_v - rho_vs))

    def test_no_fog_above_the_dew_point(self):
        self.assertEqual(self.lwc(10, 12), 0.0)

    def test_dense_fog_from_a_small_supercooling(self):
        # 0.3 C below a 10 C dew point: ~0.17 g/m3, Kunkel sigma ~30 /km,
        # a WMO visibility of ~100 m: dense fog.
        lwc = self.lwc(10, 9.7)
        sigma = 144.7 * lwc ** 0.88
        self.assertTrue(0.1 < lwc < 0.25, lwc)
        self.assertTrue(50 < 3.0 / sigma * 1000 < 200)

    def test_sqf_carries_the_relations(self):
        for token in ("144.7 * (_lwc ^ 0.88)", "min 0.5", "R_WATER_VAPOUR", "currentVapourPressure"):
            self.assertIn(token, FOG)
        for token in ("dayTime", "_hour > 7", "_spread < 3"):
            self.assertNotIn(token, FOG)


class TestHaze(unittest.TestCase):
    def test_upp_clear_air_visibility(self):
        self.assertIn("90 * exp (-2.5 * _q)", HAZE)
        self.assertIn("((_humidity / 100) - 0.15) max 0) min 0.8", HAZE)
        # Dry air 90 km; saturated 90 e^-2 = 12.2 km.
        self.assertAlmostEqual(90 * math.exp(-2.5 * 0.8), 12.18, places=2)


if __name__ == "__main__":
    unittest.main()
