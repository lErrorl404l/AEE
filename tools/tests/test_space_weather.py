#!/usr/bin/env python3
"""Space weather is driven by real records (SILSO, NOAA, GFZ, GOES).

Checks the derived corpus against facts of the record and the runtime
kernel's wiring.

Run: python3 -m unittest tools.tests.test_space_weather
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools import gen_space_weather as gen  # noqa: E402

C = json.loads(gen.CORPUS.read_text(encoding="utf-8"))
SRC = (REPO / "addons/weather/functions/climatology/fnc_calculateSpaceWeather.sqf").read_text(encoding="utf-8")


def ssn(year: int, month: int) -> float:
    return C["ssn_monthly"][(year - C["ssn_first_year"]) * 12 + month - 1]


class TestCorpus(unittest.TestCase):
    def test_runtime_table_is_fresh(self):
        self.assertEqual(gen.main(["--check"]), 0)

    def test_known_solar_maxima_and_minima(self):
        # SILSO V2 smoothed: SC22 max 212.5 (1989-11), SC24 max 116.4
        # (2014-04), SC24/25 minimum 1.8 (2019-12).
        self.assertAlmostEqual(ssn(1989, 11), 212.5, delta=1.0)
        self.assertAlmostEqual(ssn(2014, 4), 116.4, delta=1.0)
        self.assertLess(ssn(2019, 12), 3.0)

    def test_cycle_statistics(self):
        # Mean cycle ~11 years; mean SILSO V2 maximum ~179.
        self.assertAlmostEqual(C["mean_cycle_months"] / 12, 11.0, delta=0.3)
        self.assertAlmostEqual(C["mean_cycle_max"], 179, delta=10)

    def test_future_cycles_are_plausible(self):
        tail = C["ssn_monthly"][-12 * 100:]
        self.assertLess(max(tail), 300)
        self.assertGreater(max(tail), 100)

    def test_flare_rates(self):
        f = C["flares"]
        m100 = f["M"]["rate_a"] * 100 ** f["M"]["rate_b"]
        x100 = f["X"]["rate_a"] * 100 ** f["X"]["rate_b"]
        # GOES 1976-2016: an SSN-100 year has ~1-2 hundred M and ~10-15 X flares.
        self.assertTrue(100 < m100 < 250, m100)
        self.assertTrue(5 < x100 < 25, x100)
        self.assertGreater(f["M"]["events"], 5000)

    def test_kp_rows_are_distributions(self):
        for b in C["kp_transition_cumulative"]:
            for row in b:
                self.assertAlmostEqual(row[-1], 1.0, places=4)
                self.assertTrue(all(x <= y + 1e-9 for x, y in zip(row, row[1:])))
        # Storms are more likely in the high-SSN bin.
        lo, hi = C["kp_transition_cumulative"][0], C["kp_transition_cumulative"][-1]
        self.assertGreater(hi[12][15], 0)
        self.assertLess(hi[12][14], lo[12][14] + 1e-9)


class TestRuntime(unittest.TestCase):
    def test_uses_the_records_and_noaa_relations(self):
        for token in ("getSpaceWeatherData", "(10 * (log _flux)) + 65", "((sin _sunElev) ^ 0.75)",
                      "66 - 2 * _kp", "geomagneticLatitude", "_sunElev < -12",
                      "QGVAR(sunspotOverride)", "QGVAR(kpOverride)"):
            self.assertIn(token, SRC)
        for token in ("FlareChance", "sin (360 * _totalDays / 4018)", "dayTime < 6"):
            self.assertNotIn(token, SRC)


if __name__ == "__main__":
    unittest.main()
