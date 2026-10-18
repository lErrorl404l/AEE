#!/usr/bin/env python3
"""Hemisphere-correct seasons: fnc_seasonalMonth and its users, and the
water-limited foliage timing (Bagnouls & Gaussen dry months).

Run: python3 -m unittest tools.tests.test_seasons -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

HELPER = REPO / "addons/lib/functions/fnc_seasonalMonth.sqf"
FOLIAGE = REPO / "addons/weather/functions/biome/fnc_updateSeasonalFoliage.sqf"
USERS = (
    REPO / "addons/weather/functions/terrain/fnc_calculateCropState.sqf",
    REPO / "addons/weather/functions/warnings/fnc_calculateBiologicalAmbient.sqf",
    FOLIAGE,
)


class TestSeasonalMonth(unittest.TestCase):
    def test_north_is_unchanged(self):
        for m in range(1, 13):
            self.assertEqual(run_sqf(HELPER, [m, 51]), m)

    def test_south_is_six_months_out(self):
        self.assertEqual(run_sqf(HELPER, [1, -35]), 7)
        self.assertEqual(run_sqf(HELPER, [7, -35]), 1)
        self.assertEqual(run_sqf(HELPER, [12, -35]), 6)

    def test_users_apply_it(self):
        for p in USERS:
            self.assertIn("EFUNC(lib,seasonalMonth)", p.read_text(encoding="utf-8"), p.name)

    def test_december_is_winter_in_the_ambient(self):
        src = USERS[1].read_text(encoding="utf-8")
        self.assertIn("_sMonth == 12 || _sMonth <= 2", src)


class TestWaterLimitedFoliage(unittest.TestCase):
    def test_uses_the_gaussen_dry_month_on_the_station_normals(self):
        src = FOLIAGE.read_text(encoding="utf-8")
        self.assertIn("FUNC(getClimateNormals)", src)
        self.assertIn(">= (2 * _t)", src)

    def test_gaussen_on_a_real_mediterranean_station(self):
        # Madrid Retiro normals (CfgClimateStations): green Nov-May, dry Jul-Sep.
        import re
        txt = (REPO / "addons/weather/CfgClimateStations.hpp").read_text(encoding="utf-8")
        m = re.search(r'name = "MADRIDRETIRO";.*?tmax\[\] = \{([^}]*)\}; tmin\[\] = \{([^}]*)\}; prcp\[\] = \{([^}]*)\}', txt)
        tx, tn, p = ([float(v) for v in g.split(",")] for g in m.groups())
        wet = [p[k] >= 2 * (tx[k] + tn[k]) / 2 for k in range(12)]
        self.assertTrue(all(wet[k] for k in (0, 1, 10, 11)))
        self.assertFalse(any(wet[k] for k in (6, 7, 8)))


if __name__ == "__main__":
    unittest.main()
