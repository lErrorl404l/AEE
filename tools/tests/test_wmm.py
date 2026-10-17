#!/usr/bin/env python3
"""World Magnetic Model WMM2025 (issue: compass declination realism).

The compass declination is the NOAA/BGS World Magnetic Model, generated
from data/magnetism/WMM2025.COF.  These tests EXECUTE the generated SQF
kernel (tools/tests/sqf_lite.py) on NOAA's official test values, so the
check is the mod's own code against the published model.

Run: python3 -m unittest tools.tests.test_wmm
"""

from __future__ import annotations

import datetime
import math
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools import gen_wmm  # noqa: E402
from tools.tests.sqf_lite import run_sqf  # noqa: E402

KERNEL = REPO / "addons/magnetism/functions/fnc_wmmField.sqf"
COMPASS = REPO / "addons/magnetism/functions/fnc_calculateCompassDeviation.sqf"
CIVIL = REPO / "addons/lib/functions/fnc_civilDayNumber.sqf"

# A field with a distinct declination, so a test can tell which quantity the
# function publishes where: [D, I, H, X, Y, Z] in degrees and nanotesla.
FIELD = [-2.5, 66.0, 50000.0, 49000.0, -2000.0, 48000.0]


def compass(date, *, ferrous=True, anomaly_nt=-25000.0, nearby=("truck",), field=None):
    """Run the real compass function against a stubbed field and world.

    Returns (return value, the published missionNamespace state, the arguments
    the WMM kernel was called with).  The stubs are engine reads only; the
    arithmetic under test is the shipped SQF.
    """
    state = {"__QGVAR__wmmCache": ["", []]}  # a stale cache entry: recompute
    seen: dict = {}
    if not ferrous:
        state["__QGVAR__compassFerrousDeviation"] = False

    def wmm(lat, lon, alt, year):
        seen.update(lat=lat, lon=lon, alt=alt, year=year)
        return list(field or FIELD)

    out = run_sqf(
        COMPASS,
        [],
        {
            "CBA_fnc_currentUnit": lambda: "unit",
            "isNull": lambda u: u is None,
            "date": list(date),
            "missionNamespace": state,
            "worldName": "Altis",
            "getPosASL": lambda obj: [1000.0, 2000.0, 100.0],
            "vehicle": lambda u: None,
            "nearestObjects": lambda spec: list(nearby),
            "__FUNC__wmmField": wmm,
            "__FUNC__calculateMagneticAnomaly": lambda a, b: anomaly_nt,
            "__EFUNC__lib_getGeoAnchor": lambda: "anchor",
            "__EFUNC__lib_worldToMgrs": lambda pos, anchor, mode: ["GRID", 51.5, -0.1],
            "__EFUNC__lib_getWorldLocation": lambda: [51.5, 0.0, -0.1],
            "__EFUNC__lib_civilDayNumber": lambda *a: run_sqf(CIVIL, list(a)),
        },
        float32=True,
    )
    return out, state, seen


def naive_day_of_year(year, month, day):
    """The formula the compass used before the shared day count: one day low
    from 1 March in a leap year."""
    return math.floor(275 * month / 9) - 2 * math.floor((month + 9) / 12) + day - 30


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
        src = (
            REPO / "addons/magnetism/functions/fnc_calculateCompassDeviation.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn("call FUNC(wmmField)", src)
        self.assertIn("QGVAR(wmmExtrapolate)", src)
        self.assertIn("worldToMgrs", src)
        self.assertIn("date params", src)
        self.assertIn("atan (_anomalyNT / _horizontalNT)", src)
        self.assertNotIn("private _table = [", src)


class TestCompassDeclinationIsNotTheDeviation(unittest.TestCase):
    """F2: the declination and the compass deviation are different quantities.

    The map's north rose reads EGVAR(core,magneticDeclinationDeg), the
    geophysical declination.  A truck parked next to the observer must move the
    compass reading, GVAR(compassDeviation), and must not move the declination.
    """

    def test_the_declination_is_unaffected_by_the_ferrous_term(self):
        _out, state, _seen = compass([2024, 3, 1, 0, 0], anomaly_nt=-25000.0)
        # The WMM declination alone, whatever the local iron does.
        self.assertAlmostEqual(
            state["__QEGVAR__core_magneticDeclinationDeg"], FIELD[0], places=4
        )

    def test_the_deviation_carries_the_ferrous_term(self):
        out, state, _seen = compass([2024, 3, 1, 0, 0], anomaly_nt=-25000.0)
        # atan(-25000 / 50000) = -26.57 deg, capped at the -10 deg clamp.
        self.assertAlmostEqual(
            state["__QGVAR__compassDeviation"], FIELD[0] - 10.0, places=4
        )
        self.assertAlmostEqual(out, FIELD[0] - 10.0, places=4)

    def test_no_local_iron_means_deviation_equals_declination(self):
        out, state, _seen = compass([2024, 3, 1, 0, 0], nearby=())
        self.assertAlmostEqual(state["__QGVAR__compassDeviation"], FIELD[0], places=4)
        self.assertAlmostEqual(
            state["__QEGVAR__core_magneticDeclinationDeg"], FIELD[0], places=4
        )
        self.assertAlmostEqual(out, FIELD[0], places=4)

    def test_turning_the_ferrous_model_off_leaves_the_declination_alone(self):
        _out, on, _seen = compass([2024, 3, 1, 0, 0], anomaly_nt=-25000.0)
        _out2, off, _seen2 = compass([2024, 3, 1, 0, 0], ferrous=False)
        self.assertEqual(
            on["__QEGVAR__core_magneticDeclinationDeg"],
            off["__QEGVAR__core_magneticDeclinationDeg"],
        )
        self.assertNotEqual(
            on["__QGVAR__compassDeviation"], off["__QGVAR__compassDeviation"]
        )


class TestCompassDecimalYear(unittest.TestCase):
    """F3: the decimal year uses the shared exact day count.

    The naive day-of-year formula is one day low from 1 March in a leap year,
    which evaluates the WMM secular variation 0.0027 yr early for ten months of
    every leap year.
    """

    def test_civil_day_number_matches_the_calendar(self):
        for y, m, d in (
            (2024, 1, 1),
            (2024, 2, 29),
            (2024, 3, 1),
            (2024, 12, 31),
            (2025, 3, 1),
            (2000, 3, 1),
            (1999, 12, 31),
        ):
            with self.subTest(date=(y, m, d)):
                want = datetime.date(y, m, d).timetuple().tm_yday
                got = run_sqf(CIVIL, [y, m, d]) - run_sqf(CIVIL, [y, 1, 1]) + 1
                self.assertEqual(int(got), want)
                self.assertEqual(
                    int(got),
                    datetime.date(y, m, d).toordinal()
                    - datetime.date(y, 1, 1).toordinal()
                    + 1,
                )

    def test_the_compass_passes_the_exact_day_of_year_to_the_model(self):
        # 2024-03-01 is day 61 of a leap year, day 60 by the naive formula.
        _out, _state, seen = compass([2024, 3, 1, 0, 0])
        want = 2024 + (61 - 1) / 365.25
        naive = 2024 + (naive_day_of_year(2024, 3, 1) - 1) / 365.25
        self.assertAlmostEqual(seen["year"], want, delta=1e-3)
        self.assertGreater(abs(seen["year"] - naive), 2e-3)
        self.assertGreater(naive_day_of_year(2024, 3, 1), 0)

    def test_a_non_leap_year_is_unchanged(self):
        # The naive formula is exact for January and February and for every
        # non-leap year, so 2025-03-01 must still read day 60.
        _out, _state, seen = compass([2025, 3, 1, 0, 0])
        self.assertAlmostEqual(seen["year"], 2025 + (60 - 1) / 365.25, delta=1e-3)

    def test_the_midnight_date_is_the_mission_date(self):
        _out, _state, seen = compass([2025, 6, 15, 12, 30])
        want = 2025 + ((166 - 1) + (12 + 30 / 60) / 24) / 365.25
        self.assertAlmostEqual(seen["year"], want, delta=1e-3)


class TestWmmPoles(unittest.TestCase):
    """F7: the (north, east) frame is singular at a geographic pole.

    cos(latC) is zero there and every P(n,m) with m > 0 vanishes with it, so the
    east term is a 0/0 whose float32 value is rounding noise.  The pole is a
    special case: D, H, X and Y are reported as 0, I is +-90, Z is exact.
    """

    def test_the_north_pole_is_finite_and_axial(self):
        d, i, h, x, y, z = run_sqf(KERNEL, [90, 0, 0, 2025], {}, float32=True)
        for value in (d, i, h, x, y, z):
            self.assertTrue(math.isfinite(value))
        self.assertAlmostEqual(d, 0.0, places=6)
        self.assertAlmostEqual(i, 90.0, places=4)
        self.assertAlmostEqual(h, 0.0, places=6)
        self.assertAlmostEqual(x, 0.0, places=6)
        self.assertAlmostEqual(y, 0.0, places=6)
        self.assertGreater(z, 50000.0)  # the axial field, down positive

    def test_the_south_pole_is_finite_and_axial(self):
        d, i, h, x, y, z = run_sqf(KERNEL, [-90, 0, 0, 2025], {}, float32=True)
        for value in (d, i, h, x, y, z):
            self.assertTrue(math.isfinite(value))
        self.assertAlmostEqual(d, 0.0, places=6)
        self.assertAlmostEqual(i, -90.0, places=4)
        self.assertAlmostEqual(x, 0.0, places=6)
        self.assertAlmostEqual(y, 0.0, places=6)
        self.assertLess(z, -50000.0)

    def test_the_guard_does_not_spill_away_from_the_pole(self):
        # 89.99 deg is outside the guard: the field is the ordinary model, with
        # a nonzero horizontal intensity.
        d, _i, h, _x, _y, z = run_sqf(KERNEL, [89.99, 0, 0, 2025], {}, float32=True)
        self.assertGreater(h, 100.0)
        self.assertNotEqual(d, 0.0)
        self.assertGreater(z, 50000.0)

    def test_the_pole_path_agrees_in_the_axial_component(self):
        # Z is exact at the pole: a hair off it must give the same Z.
        _d, _i, _h, _x, _y, z_pole = run_sqf(KERNEL, [90, 0, 0, 2025], {}, float32=True)
        _d, _i, _h, _x, _y, z_near = run_sqf(
            KERNEL, [89.999, 0, 0, 2025], {}, float32=True
        )
        self.assertAlmostEqual(z_pole, z_near, delta=1.0)


if __name__ == "__main__":
    unittest.main()
