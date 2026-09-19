#!/usr/bin/env python3
"""Reference checks for the cold-weather human performance model.

Validates the SQF implementation in addons/physiology:
- fnc_calculateColdWeatherPerformance.sqf
  (wind chill -> dexterity, frostbite time, TB MED 508 danger category)

Ground truth (research-verified):
- Wind chill: Osczevski & Bluestein 2001, NWS/Environment Canada metric
  formula.  Valid for T <= 10 degC and V > 4.8 km/h.
- Manual dexterity: Heus, Daanen & Havenith 1995, Appl Ergon 26(1):5-13,
  PMID 15676995; Daanen 2009.  90 % at 0 degC wind chill, 2 % per degC
  loss, 10 % floor at -40 degC.
- Frostbite time: Tikuisis & Osczevski 2002, J. Appl. Meteor. 41:1226;
  anchored to the NOAA / US Army Research Institute frostbite chart.
  t = 90 * exp(0.11 * WCT) minutes, floor 1 minute.
- Danger categories: TB MED 508, Prevention and Management of Cold
  Weather Injuries.

Run: python3 -m unittest tools/tests/test_cold_weather.py
"""

import math
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PHYSIOLOGY = _REPO_ROOT / "addons" / "physiology" / "functions"

def _read_recursive(base, name):
    """Read an SQF function file, resolving categorised subfolders (issue
    #203).  The function NAME is flat (aee_<mod>_fnc_<name>)."""
    if (base / name).exists():
        return (base / name).read_text(encoding="utf-8")
    for f in base.rglob(name):
        return f.read_text(encoding="utf-8")
    raise FileNotFoundError(f"{name} not found under {base}")


# Piecewise-linear dexterity anchors (WCT degC -> dexterity %).  The SQF
# uses the equivalent closed form 90 + 2*WCT with a 10 % floor.
_DEXTERITY_ANCHORS = [
    (0.0, 90.0),
    (-10.0, 70.0),
    (-20.0, 50.0),
    (-30.0, 30.0),
    (-40.0, 10.0),
]


def wind_chill(temp_c, wind_kmh):
    """Mirror of the Osczevski-Bluestein branch in fnc_calculateColdWeatherPerformance."""
    if temp_c <= 10 and wind_kmh > 4.8:
        v_exp = wind_kmh**0.16
        chill = 13.12 + 0.6215 * temp_c - 11.37 * v_exp + 0.3965 * temp_c * v_exp
        return min(chill, temp_c)
    return temp_c


def dexterity_percent(wct):
    """Mirror of the dexterity curve in fnc_calculateColdWeatherPerformance."""
    if wct < 0:
        return max(10.0, 90.0 + 2.0 * wct)
    return 90.0


def frostbite_minutes(wct):
    """Mirror of the frostbite time model in fnc_calculateColdWeatherPerformance."""
    return max(1.0, 90.0 * math.exp(0.11 * wct))


def cold_danger_category(wct):
    """Mirror of the TB MED 508 category branches in fnc_calculateColdWeatherPerformance."""
    if wct < -54:
        return "immediate"
    if wct < -39:
        return "great"
    if wct < -28:
        return "increased"
    return "little"


class TestWindChill(unittest.TestCase):
    """Osczevski-Bluestein wind chill (NWS/Environment Canada 2001)."""

    def test_wind_chill_zero_ten_kmh(self):
        # T = 0 degC, V = 10 km/h -> -3.31 degC.
        self.assertAlmostEqual(wind_chill(0.0, 10.0), -3.31, places=2)

    def test_wind_chill_minus10_thirty_kmh(self):
        # T = -10 degC, V = 30 km/h -> -19.52 degC.
        self.assertAlmostEqual(wind_chill(-10.0, 30.0), -19.52, places=2)

    def test_no_wind_chill_when_warm(self):
        # T > 10 degC: the formula does not apply, ambient is returned.
        self.assertEqual(wind_chill(15.0, 40.0), 15.0)
        self.assertEqual(wind_chill(10.1, 40.0), 10.1)

    def test_no_wind_chill_when_calm(self):
        # V <= 4.8 km/h: no meaningful chilling, ambient is returned.
        self.assertEqual(wind_chill(-20.0, 4.8), -20.0)
        self.assertEqual(wind_chill(-20.0, 4.0), -20.0)

    def test_wind_chill_never_warmer_than_air(self):
        for t in (-40, -20, -10, 0, 5, 10):
            for v in (5, 10, 30, 60):
                self.assertLessEqual(wind_chill(t, v), t)


class TestDexterity(unittest.TestCase):
    """Manual dexterity curve (Heus 1995, Daanen 2009)."""

    def test_anchor_points(self):
        for wct, expected in _DEXTERITY_ANCHORS:
            self.assertAlmostEqual(dexterity_percent(wct), expected, places=4)

    def test_warm_flat(self):
        # At and above 0 degC wind chill, dexterity is a mild 90 %.
        self.assertAlmostEqual(dexterity_percent(0.0), 90.0, places=4)
        self.assertAlmostEqual(dexterity_percent(10.0), 90.0, places=4)

    def test_mild_cold_over_80(self):
        # T = 0, V = 10 km/h -> WCT -3.31 -> dexterity ~83 % (> 80).
        wct = wind_chill(0.0, 10.0)
        self.assertGreater(dexterity_percent(wct), 80.0)

    def test_moderate_cold_about_50(self):
        # T = -10, V = 30 km/h -> WCT ~ -19.5 -> dexterity ~ 51 %.
        wct = wind_chill(-10.0, 30.0)
        self.assertAlmostEqual(dexterity_percent(wct), 51.0, delta=1.5)

    def test_severe_cold_under_30(self):
        # T = -20, V = 40 km/h -> WCT ~ -34 -> dexterity < 30 %.
        wct = wind_chill(-20.0, 40.0)
        self.assertLess(dexterity_percent(wct), 30.0)

    def test_floor(self):
        self.assertAlmostEqual(dexterity_percent(-40.0), 10.0, places=4)
        self.assertAlmostEqual(dexterity_percent(-60.0), 10.0, places=4)

    def test_monotonic(self):
        prev = dexterity_percent(10.0)
        for wct in range(0, -61, -5):
            cur = dexterity_percent(float(wct))
            self.assertLessEqual(cur, prev)
            prev = cur


class TestFrostbite(unittest.TestCase):
    """Frostbite time-to-injury (Tikuisis & Osczevski 2002)."""

    def test_anchors(self):
        # -10 -> ~30 min, -20 -> ~10 min.
        self.assertAlmostEqual(frostbite_minutes(-10.0), 30.0, delta=1.0)
        self.assertAlmostEqual(frostbite_minutes(-20.0), 10.0, delta=1.0)

    def test_minus30(self):
        # -30 -> 90 * exp(-3.3) ~ 3.3 min.
        self.assertAlmostEqual(
            frostbite_minutes(-30.0), 90.0 * math.exp(-3.3), places=4
        )

    def test_floor(self):
        self.assertGreaterEqual(frostbite_minutes(-100.0), 1.0)

    def test_decreasing(self):
        prev = frostbite_minutes(0.0)
        for wct in range(-5, -61, -5):
            cur = frostbite_minutes(float(wct))
            self.assertLessEqual(cur, prev)
            prev = cur


class TestDangerCategory(unittest.TestCase):
    """TB MED 508 danger categories."""

    def test_boundaries(self):
        self.assertEqual(cold_danger_category(-27.9), "little")
        self.assertEqual(cold_danger_category(-28.0), "little")
        self.assertEqual(cold_danger_category(-28.1), "increased")
        self.assertEqual(cold_danger_category(-39.0), "increased")
        self.assertEqual(cold_danger_category(-39.1), "great")
        self.assertEqual(cold_danger_category(-54.0), "great")
        self.assertEqual(cold_danger_category(-54.1), "immediate")

    def test_extremes(self):
        self.assertEqual(cold_danger_category(10.0), "little")
        self.assertEqual(cold_danger_category(-80.0), "immediate")


class TestDockerContract(unittest.TestCase):
    """Lock the four PHASE23 docker cases to the mirror."""

    def test_phase23_cases(self):
        # Case 1: mild cold.
        wct = wind_chill(0.0, 10.0)
        self.assertAlmostEqual(wct, -3.0, delta=1.0)
        self.assertGreater(dexterity_percent(wct), 80.0)
        self.assertGreater(frostbite_minutes(wct), 60.0)

        # Case 2: moderate cold.
        wct = wind_chill(-10.0, 30.0)
        self.assertAlmostEqual(wct, -20.0, delta=3.0)
        self.assertAlmostEqual(dexterity_percent(wct), 50.0, delta=5.0)
        self.assertAlmostEqual(frostbite_minutes(wct), 10.0, delta=5.0)

        # Case 3: severe cold.
        wct = wind_chill(-20.0, 40.0)
        self.assertAlmostEqual(wct, -35.0, delta=5.0)
        self.assertLess(dexterity_percent(wct), 30.0)
        self.assertLess(frostbite_minutes(wct), 5.0)

        # Case 4: warm, no wind chill.
        self.assertEqual(wind_chill(15.0, 10.0), 15.0)


class TestSQFSyncColdWeather(unittest.TestCase):
    """SQF source must contain the constants the Python mirror relies on."""

    def _assert_in_sqf(self, fragments, context):
        text = _read_recursive(_PHYSIOLOGY, "fnc_calculateColdWeatherPerformance.sqf")
        missing = [f for f in fragments if f not in text]
        self.assertFalse(
            missing,
            f"fnc_calculateColdWeatherPerformance.sqf: {context} changed/missing "
            f"in SQF: {missing}. Re-sync the Python mirror in test_cold_weather.py.",
        )

    def test_wind_chill_constants(self):
        self._assert_in_sqf(
            [
                "* 3.6",
                "_windKmh > 4.8",
                "_tempC <= 10",
                "13.12 + 0.6215",
                "11.37 * _vExp",
                "0.3965 * _tempC * _vExp",
                "_windKmh ^ 0.16",
            ],
            "Osczevski-Bluestein wind chill constants",
        )

    def test_dexterity_constants(self):
        self._assert_in_sqf(
            ["(90 + 2 * _wct) max 10"],
            "dexterity slope and floor",
        )

    def test_frostbite_constants(self):
        self._assert_in_sqf(
            ["(90 * exp (0.11 * _wct)) max 1"],
            "frostbite exponential model and floor",
        )

    def test_category_and_outputs(self):
        self._assert_in_sqf(
            [
                "_wct < -28",
                "_wct < -39",
                "_wct < -54",
                "coldWeatherEnabled",
                "windChillTemp",
                "dexterityPercent",
                "frostbiteMinutes",
                "coldDangerCategory",
            ],
            "TB MED 508 thresholds, setting and output variables",
        )


if __name__ == "__main__":
    unittest.main()
