#!/usr/bin/env python3
"""Hemisphere-correct seasons: fnc_seasonalMonth and its users, and the
water-limited foliage timing (Bagnouls & Gaussen dry months).

Run: python3 -m unittest tools.tests.test_seasons -v
"""

from __future__ import annotations

import math
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

HELPER = REPO / "addons/lib/functions/fnc_seasonalMonth.sqf"
FOLIAGE = REPO / "addons/weather/functions/biome/fnc_updateSeasonalFoliage.sqf"
# The foliage kernel is NOT here: its phenology is driven by the station's
# own normals, so it needs no hemisphere shift (see its header).
USERS = (
    REPO / "addons/weather/functions/terrain/fnc_calculateCropState.sqf",
    REPO / "addons/weather/functions/warnings/fnc_calculateBiologicalAmbient.sqf",
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


class TestFoliagePhenology(unittest.TestCase):
    def test_the_foliage_kernel_holds_no_hard_coded_month_row(self):
        src = FOLIAGE.read_text(encoding="utf-8")
        code = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
        code = "\n".join(l.split("//")[0] for l in code.splitlines())
        # A twelve-number literal row would be an invented phenology.
        self.assertNotRegex(code, r"\[\s*0?\.?\d+\s*(,\s*0?\.?\d+\s*){11}\]"
                            .replace("0?", "[01]?"))
        self.assertIn("FUNC(getClimateNormals)", code)

    def test_the_cover_maxima_are_the_ornl_lai_through_beer_lambert(self):
        src = FOLIAGE.read_text(encoding="utf-8")
        self.assertIn("ORNL/TM-2001/268", src)
        self.assertIn("Monsi & Saeki 1953", src)
        for lai, cover in ((4.78, 0.908), (3.92, 0.859), (1.71, 0.575),
                           (2.08, 0.646), (5.06, 0.920), (2.65, 0.734),
                           (1.88, 0.609)):
            with self.subTest(lai=lai):
                self.assertAlmostEqual(1 - math.exp(-0.5 * lai), cover, delta=0.001)
                self.assertIn(f"{cover:.3f}", src)

    def test_the_summergreen_ramp_is_the_lpj_model(self):
        src = FOLIAGE.read_text(encoding="utf-8")
        self.assertIn("Sitch", src)
        self.assertIn("_gdd5 / 200", src)
        # The 5 C base is the subtrahend of the degree-day term, not a
        # comparison: a month at or below the base contributes nothing
        # because the excess is clamped at zero. An earlier draft of this
        # assertion looked for a bare "< 5", which the kernel never held.
        self.assertIn("([_m] call _meanT) - 5) max 0", src)

    def test_uses_the_gaussen_dry_month_on_the_station_normals(self):
        src = FOLIAGE.read_text(encoding="utf-8")
        self.assertIn("FUNC(getClimateNormals)", src)
        self.assertIn(">= (2 * ([_m] call _meanT))", src)

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
